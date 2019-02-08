
#include <cstdint>
#include <cstdio>
#include <signal.h>
#include <thread>
#include "Configuration.h"
#include <Aeron.h>


extern "C"{
#include <stdarg.h>
#include "aeronlib.h"
}


using namespace aeron::util;
using namespace aeron;


// Header:
// Num of flows
// Flow:
// throughput
// Num of links
// id's of links



int FRAGMENT_COUNT_LIMIT = 10;
static const std::chrono::duration<long, std::milli> IDLE_SLEEP_MS(1);

//typedef std::array<std::uint8_t, 256> buffer_t;
typedef std::array<int, 256> buffer_t;
//typedef std::vector<std::tuple<int, std::vector<int>>> flow_array;
//typedef std::vector<std::tuple<int, int, int*>> flow_array;


void (*g_callback)(int, int, int*) = nullptr;


struct Settings {
    std::string dirPrefix = "";
    std::string channel = "aeron:ipc";
    std::int32_t streamId = 0;
    std::int32_t processesCount = 1;
    int messageLength = 256;
};


std::atomic<bool> running (true);

Settings settings;
aeron::Context context;
std::shared_ptr<Aeron> aeronPtr;

std::int64_t subscriptionId, publicationId;
std::shared_ptr<Publication> publication;
std::shared_ptr<Subscription> subscription;
std::shared_ptr<std::thread> pollThread;

std::vector<std::shared_ptr<Subscription>> subscriptions;


int *receiveBuffer;
int sendBuffer[256];
int idx;


void printFlow(int throughput, int linkCount, int* linkList) {
    std::cout << "C++: throughput: " << throughput << "; for links: ";

    for (int i = 0; i < linkCount; i++)
        std::cout << linkList[i] << " ";

    std::cout << std::endl;
}


void printFlowArray(int *array, int length) {
    int ptr = 0;
    int flowCount = array[ptr++];
    int throughput, linkCount;

    std::cout << "C++: collected " << flowCount << " flows: " << std::endl;

    for (int f = 0; f < flowCount; ++f) {
        throughput = array[ptr++];
        linkCount = array[ptr++];

        std::cout << "throughput: " << throughput << "; for links:";
        for (int i = 0; i < linkCount; ++i)
            std::cout << " " << array[ptr++];

        std::cout << std::endl;
    }

    std::cout << std::endl;
}




fragment_handler_t printStringMessage() {
    return [&](const AtomicBuffer& buffer, util::index_t offset, util::index_t length, const Header& header) {
		
// 		int *message = reinterpret_cast<int*>(buffer.buffer()) + offset/sizeof(int);
		receiveBuffer = reinterpret_cast<int*>(buffer.buffer()) + offset/sizeof(int);
		
//         std::cout << "from stream " << header.streamId();
//         std::cout << " offset " << offset << " length " << length << " <<\n";
//         printFlowArray(receiveBuffer, length);
// 		std::cout << ">>" << std::endl;
		
		int ptr = 0;
		int bandwidth, linkCount;
		int flowCount = receiveBuffer[ptr++];
		for (int f = 0; f < flowCount; ++f) {
			bandwidth = receiveBuffer[ptr++];
			linkCount = receiveBuffer[ptr++];
			if (g_callback)
				(*g_callback)(bandwidth, linkCount, &(receiveBuffer[ptr]));
			
			ptr += linkCount;
		}
    };
}

void printEndOfStream(Image &image) {
    std::cout << "End Of Stream image correlationId=" << image.correlationId()
        << " sessionId=" << image.sessionId()
        << " from " << image.sourceIdentity()
        << std::endl;
}




void setupContextHandlers(aeron::Context &context) {
    context.newPublicationHandler(
        [](const std::string& channel, std::int32_t streamId, std::int32_t sessionId, std::int64_t correlationId) {
            std::cout << "Publication: " << channel << " " << correlationId << ":" << streamId << ":" << sessionId << std::endl;
        });

    context.newSubscriptionHandler(
        [](const std::string& channel, std::int32_t streamId, std::int64_t correlationId) {
            std::cout << "Subscription: " << channel << " " << correlationId << ":" << streamId << std::endl;
        });

    context.availableImageHandler([](Image &image) {
            std::cout << "Available image correlationId=" << image.correlationId() << " sessionId=" << image.sessionId();
            std::cout << " at position=" << image.position() << " from " << image.sourceIdentity() << std::endl;
        });

    context.unavailableImageHandler([](Image &image) {
            std::cout << "Unavailable image on correlationId=" << image.correlationId() << " sessionId=" << image.sessionId();
            std::cout << " at position=" << image.position() << " from " << image.sourceIdentity() << std::endl;
        });
}



void init(int stream_id, int processesCount, int *ids_list) {

    std::cout << "\nC++: started." << std::endl;

    idx = 0;
    sendBuffer[idx++] = 0;

    settings.streamId = stream_id;
    settings.processesCount = processesCount;

    try {
        setupContextHandlers(context);
        aeronPtr = Aeron::connect(context);

        publicationId = aeronPtr->addPublication(settings.channel, settings.streamId);
        subscriptionId = aeronPtr->addSubscription(settings.channel, settings.streamId);

        publication = aeronPtr->findPublication(publicationId);
        while (!publication) {
            std::this_thread::yield();
            publication = aeronPtr->findPublication(publicationId);
        }
        
        std::vector<std::int64_t> subIds;
		for (int k = 0; k <= settings.processesCount; k++) {
			if (k != settings.streamId)
				subIds.push_back(aeronPtr->addSubscription(settings.channel, ids_list[k]));
		}
		
		std::shared_ptr<Subscription> sub;	
		for (int i = 0; i < subIds.size(); i++) {
			sub = aeronPtr->findSubscription(subIds[i]);
			while (!sub) {
				std::this_thread::yield();
				sub = aeronPtr->findSubscription(subIds[i]);
			}
			subscriptions.push_back(sub);
		}
		
        pollThread = std::make_shared<std::thread>([]() {
            fragment_handler_t handler = printStringMessage();
            SleepingIdleStrategy idleStrategy(IDLE_SLEEP_MS);

            bool reachedEos = false;
			std::vector<std::shared_ptr<Subscription>>::iterator it;
            while (running) {
				
				for (it = subscriptions.begin(); it != subscriptions.end(); it++) {
					int fragmentsRead = (*it)->poll(handler, FRAGMENT_COUNT_LIMIT);
					
					if (fragmentsRead == 0) {
						if (!reachedEos && (*it)->pollEndOfStreams(printEndOfStream) > 0) {
							reachedEos = true;
						}
					}
					
					idleStrategy.idle(fragmentsRead);
				}
            }
        });

    } catch (const SourcedException& e) {
        std::cerr << "FAILED: " << e.what() << " : " << e.where() << std::endl;
        return;

    } catch (const std::exception& e) {
        std::cerr << "FAILED: " << e.what() << " : " << std::endl;
        return;
    }

}


void registerCallback(void(*callback)(int a, int count, int* list)) {
    g_callback = callback;
}



void addFlow(int throughput, int linkCount, int* linkList) {
    if (idx + linkCount + 2 > 256)
        flush();

    sendBuffer[idx++] = throughput;
    sendBuffer[idx++] = linkCount;
    for (int i = 0; i < linkCount; ++i)
        sendBuffer[idx++] = linkList[i];

    sendBuffer[0]++;
}


void flush() {
    std::unique_ptr<std::uint8_t[]> buffer(new std::uint8_t[settings.messageLength]);
    concurrent::AtomicBuffer srcBuffer(buffer.get(), settings.messageLength);
	
    for (int i = 0; i < idx; ++i)
        srcBuffer.putInt32(i*sizeof(std::int32_t), sendBuffer[i]);
	
    publication->offer(srcBuffer, 0, idx*sizeof(std::int32_t));

    idx = 0;
    sendBuffer[idx++] = 0;
}



void shutdown() {
    running = false;
    if (pollThread != nullptr)
        pollThread->join();

    std::cout << "\nC++: shutdown" << std::endl;
}




// deprecated
void addStuff(int singleValue, int count, int* list) {
    printFlow(singleValue, count, list);
    for (int i = 0; i < count; i++) {
        sendBuffer[idx] = list[i];
        idx++;
        sendBuffer[idx] = ' ';
        idx++;
    }
}

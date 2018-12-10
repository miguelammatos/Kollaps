#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

#include <sys/prctl.h>
#include <signal.h>

/*PID1
 *Special init process for NEED
 *Required to prevent "ragnarok" events from leaving behind zombie containers
 *The main functionality is launching the GOD and reaping all children upon its death
 */

int main(int argc, char** argv){
	prctl(PR_SET_CHILD_SUBREAPER, 1, NULL, NULL, NULL);
	
	//signal(SIGCHLD, SIG_IGN);
	//This should be enough to prevent zombies from even beeing created
	//but in our case it doesnt work (here, in god, or even in emucore)

	pid_t forked_pid;
	if(!(forked_pid = fork())){
		execv(argv[1], argv+1);
	}
	setpgid(forked_pid, 0); // Place the forked process in a new group

	int returnStatus = -1;
	pid_t pid = waitpid(forked_pid, &returnStatus, 0);
	printf("Child ended %d\n", pid);
	kill(-(forked_pid), SIGKILL);	

	sleep(5); //Just to be extra sure the processes are dead and parented to us
	
	while( waitpid(-1, &returnStatus, 0) > 0){
		printf("Grandchild reaped\n");
	}
	printf("No more children\n");
}

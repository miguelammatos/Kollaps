
import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

# Header:
# Num of flows
# Flow:
# throughput
# Num of links
# id's of links


class FlowDisseminator:
    def __init__(self, manager, flow_collector):
        self.emuliation_manager = manager
        self.flow_collector = flow_collector

    def broadcast_flows(self, active_flows):
        if len(active_flows) < 1:
            return
        """
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        pass

    def receive_flows(self, data):
        pass

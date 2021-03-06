import queue
import threading

from yowsup.layers.network import YowNetworkLayer
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStackBuilder
from yowsup.layers.auth import AuthError

from .layer import QueueLayer


class QueueStack():
    def __init__(self):
        pass

    def start(self, user, password):
        self.receiveQueue = queue.Queue()

        credentials = (user, password)  # replace with your phone and password
        stackBuilder = YowStackBuilder()

        self.stack = stackBuilder \
            .pushDefaultLayers(False) \
            .push(QueueLayer(self.receiveQueue)) \
            .build()

        self.stack.setCredentials(credentials)

        connectEvent = YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
        self.stack.broadcastEvent(connectEvent)

        try:
            threading._start_new_thread(self.stack.loop, tuple((0.5, 0.5)))
            # self.stack.loop(timeout = 0.5, discrete = 0.5)
        except AuthError as e:
            print("Auth Error, reason %s" % e)

    def sendMessage(self, number, msg):
        self.stack.broadcastEvent(YowLayerEvent(name=QueueLayer.EVENT_SEND_MESSAGE, msg=msg, number=number))

    def sendImage(self, number, path):
        self.stack.broadcastEvent(YowLayerEvent(name=QueueLayer.EVENT_SEND_IMAGE, path=path, number=number))

    def getMessage(self):
        try:
            retItem = self.receiveQueue.get(False)
        except queue.Empty:
            retItem = None
        return retItem

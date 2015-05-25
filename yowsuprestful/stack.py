from .layer import QueueLayer
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.protocol_messages import YowMessagesProtocolLayer
from yowsup.layers.protocol_receipts import YowReceiptProtocolLayer
from yowsup.layers.protocol_acks import YowAckProtocolLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.coder import YowCoderLayer
from yowsup.stacks import YowStack
from yowsup.common import YowConstants
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStack, YowStackBuilder
from yowsup import env
from yowsup.layers.auth import AuthError
import queue
import threading


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
        self.stack.broadcastEvent(YowLayerEvent(name=QueueLayer.SEND_MESSAGE, msg=msg, number=number))

    def sendImage(self, number, path):
        self.stack.broadcastEvent(YowLayerEvent(name=QueueLayer.SEND_IMAGE, path=path, number=number))

    def getMessage(self):
        try:
            retItem = self.receiveQueue.get(False)
        except queue.Empty:
            retItem = None
        return retItem

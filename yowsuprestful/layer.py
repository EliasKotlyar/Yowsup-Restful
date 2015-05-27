import sys
import os

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_receipts.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import *
from yowsup.layers.protocol_acks.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers import YowLayerEvent


class QueueLayer(YowInterfaceLayer):
    PROP_RECEIPT_AUTO = "org.openwhatsapp.yowsup.prop.cli.autoreceipt"
    PROP_RECEIPT_KEEPALIVE = "org.openwhatsapp.yowsup.prop.cli.keepalive"
    PROP_CONTACT_JID = "org.openwhatsapp.yowsup.prop.cli.contact.jid"
    EVENT_SEND_MESSAGE = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    EVENT_SEND_IMAGE = "org.openwhatsapp.yowsup.prop.queue.sendimage"

    def __init__(self, receiveQueue):
        super(QueueLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.connected = False
        self.receiveQueue = receiveQueue

    def assertConnected(self):
        if self.connected:
            return True
        else:
            return False

    @ProtocolEntityCallback("chatstate")
    def onChatstate(self, entity):
        self.output(entity)

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        self.output(entity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        # formattedDate = datetime.datetime.fromtimestamp(self.sentCache[entity.getId()][0]).strftime('%d-%m-%Y %H:%M')
        # print("%s [%s]:%s"%(self.username, formattedDate, self.sentCache[entity.getId()][1]))
        if entity.getClass() == "message":
            self.output(entity.getId())
            # self.notifyInputThread()

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        self.connected = False
        self.output("Login Failed, reason: %s" % entity.getReason())

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # send receipt otherwise we keep receiving the same message over and over

        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom())

        # outgoingMessageProtocolEntity = TextMessageProtocolEntity(
        #   messageProtocolEntity.getBody(),
        #  to=messageProtocolEntity.getFrom())
        message = messageProtocolEntity
        if message.getType() == "text":
            messageBody = message.getBody()
        elif message.getType() == "media":
            messageBody = self.getMediaMessageBody(message)
        else:
            messageBody = "Error : Unknown message type %s " % message.getType()
        retItem = {
            "body": messageBody,
            "number": message.getFrom()
        }
        self.receiveQueue.put(retItem)
        self.output("Received Message from %s : %s" % (messageProtocolEntity.getFrom(), messageBody))
        self.toLower(receipt)
        # self.toLower(outgoingMessageProtocolEntity)

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.output("Sucessfully Connected..")
        self.connected = True

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        #notificationData = notification.__str__()
        #if notificationData:
        #    self.output(notificationData)
        #else:
        #    self.output("From :%s, Type: %s" % (notification.getFrom(), notification.getType()))
        receipt = OutgoingReceiptProtocolEntity(notification.getId(), notification.getFrom())
        self.toLower(receipt)

    def onEvent(self, layerEvent):

        if layerEvent.getName() == YowNetworkLayer.EVENT_STATE_DISCONNECTED:
            self.output("Disconnected: %s" % layerEvent.getArg("reason"))
            self.connected = False
            connectEvent = YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
            self.getStack().broadcastEvent(connectEvent)

        if self.assertConnected():
            if layerEvent.getName() == self.__class__.EVENT_SEND_MESSAGE:
                msg = layerEvent.getArg("msg")
                number = layerEvent.getArg("number")
                self.output("Send Message to %s : %s" % (number, msg))
                jid = self.aliasToJid(number)
                outgoingMessageProtocolEntity = TextMessageProtocolEntity(
                    msg,
                    to=jid)
                self.toLower(outgoingMessageProtocolEntity)
            if layerEvent.getName() == self.__class__.EVENT_SEND_IMAGE:
                path = layerEvent.getArg("path")
                number = layerEvent.getArg("number")
                jid = self.aliasToJid(number)
                entity = RequestUploadIqProtocolEntity(RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE, filePath=path)
                successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(jid, path, successEntity,
                                                                                         originalEntity)
                errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(jid, path, errorEntity,
                                                                                    originalEntity)
                self._sendIq(entity, successFn, errorFn)

    def getMediaMessageBody(self, message):

        if message.getMediaType() in ("image", "audio", "video"):
            return self.getDownloadableMediaMessageBody(message)
        else:
            return "[Media Type: %s]" % message.getMediaType()

    def getDownloadableMediaMessageBody(self, message):

        return "[Media Type:{media_type}, Size:{media_size}, URL:{media_url}]".format(
            media_type=message.getMediaType(),
            media_size=message.getMediaSize(),
            media_url=message.getMediaUrl()
        )

    def aliasToJid(self, calias):

        jid = "%s@s.whatsapp.net" % calias
        return jid

    def onRequestUploadResult(self, jid, filePath, resultRequestUploadIqProtocolEntity,
                              requestUploadIqProtocolEntity):

        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendImage(filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp())
        else:
            # successFn = lambda filePath, jid, url: self.onUploadSuccess(filePath, jid, url, resultRequestUploadIqProtocolEntity.getIp())
            mediaUploader = MediaUploader(jid, self.getOwnJid(), filePath,
                                          resultRequestUploadIqProtocolEntity.getUrl(),
                                          resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                          self.onUploadSuccess, self.onUploadError, self.onUploadProgress,
                                          async=False)
            mediaUploader.start()

    def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity,
                             requestUploadIqProtocolEntity):

        self.output("Request upload for file %s for %s failed" % (path, jid))

    def doSendImage(self, filePath, url, to, ip=None):
        entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        self.toLower(entity)

    def onUploadSuccess(self, filePath, jid, url):

        self.doSendImage(filePath, url, jid)

    def onUploadError(self, filePath, jid, url):

        self.output("Upload file %s to %s for %s failed!" % (filePath, url, jid))

    def onUploadProgress(self, filePath, jid, url, progress):
        # sys.stdout.write("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        # sys.stdout.flush()
        self.output("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        # pass

    def output(self, str):

        print(str)

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity
from yowsup.layers.protocol_receipts.protocolentities import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities import OutgoingAckProtocolEntity

from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers import YowLayerEvent
from yowsup.layers.network import YowNetworkLayer
import sys
from yowsup.common import YowConstants
import datetime
import os
import logging
from yowsup.layers.protocol_receipts.protocolentities import *
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import *
from yowsup.layers.protocol_acks.protocolentities import *
from yowsup.layers.protocol_ib.protocolentities import *
from yowsup.layers.protocol_iq.protocolentities import *
from yowsup.layers.protocol_contacts.protocolentities import *
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_privacy.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_profiles.protocolentities import *
from yowsup.layers.axolotl.protocolentities.iq_key_get import GetKeysIqProtocolEntity
from yowsup.layers.axolotl import YowAxolotlLayer
from yowsup.common.tools import ModuleTools


class QueueLayer(YowInterfaceLayer):
    SEND_MESSAGE = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    SEND_IMAGE = "org.openwhatsapp.yowsup.prop.queue.sendimage"

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

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        # send receipt otherwise we keep receiving the same message over and over

        if True:
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
            print("Received Message from %s : %s" % (messageProtocolEntity.getFrom(), messageBody))
            self.toLower(receipt)
            # self.toLower(outgoingMessageProtocolEntity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", "delivery", entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.connected = True

    def onEvent(self, layerEvent):
        if self.assertConnected():
            if layerEvent.getName() == self.__class__.SEND_MESSAGE:
                msg = layerEvent.getArg("msg")
                number = layerEvent.getArg("number")
                print("Send Message to %s : %s" % (number, msg))
                jid = self.aliasToJid(number)
                outgoingMessageProtocolEntity = TextMessageProtocolEntity(
                    msg,
                    to=jid)
                self.toLower(outgoingMessageProtocolEntity)
            if layerEvent.getName() == self.__class__.SEND_IMAGE:
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

    def onRequestUploadResult(self, jid, filePath, resultRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendImage(filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp())
        else:
            # successFn = lambda filePath, jid, url: self.onUploadSuccess(filePath, jid, url, resultRequestUploadIqProtocolEntity.getIp())
            mediaUploader = MediaUploader(jid, self.getOwnJid(), filePath,
                                          resultRequestUploadIqProtocolEntity.getUrl(),
                                          resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                          self.onUploadSuccess, self.onUploadError, self.onUploadProgress, async=False)
            mediaUploader.start()

    def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity,
                             requestUploadIqProtocolEntity):
        print("Request upload for file %s for %s failed" % (path, jid))

    def doSendImage(self, filePath, url, to, ip=None):
        entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        self.toLower(entity)

    def onUploadSuccess(self, filePath, jid, url):
        self.doSendImage(filePath, url, jid)

    def onUploadError(self, filePath, jid, url):
        print("Upload file %s to %s for %s failed!" % (filePath, url, jid))

    def onUploadProgress(self, filePath, jid, url, progress):
        sys.stdout.write("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        sys.stdout.flush()

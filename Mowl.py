import poplib
import smtplib

from email.header import decode_header,Header
from email.parser import BytesParser
from email.message import Message

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

def inlineEncoder(s: str,coding='utf-8') -> str:
    return str(Header(s,coding))

def inlineDecoder(s : str) -> str:
    if not s:
        return ''
    tuple_list  : list[tuple[bytes,str]] = decode_header(s)
    text_buffer : list[str] = []
    for sub , coding in tuple_list:
        if coding == None:
            text_buffer.append(sub.decode() if type(sub)==bytes else sub)
            continue
        text_buffer.append(sub.decode(coding))
    return ''.join(text_buffer)

bytesParser = BytesParser()

class MessageDecoded:
    def __init__(self,MessageObj:Message): # Seperate payload into content & children
        self.attrs = {}
        self.message = MessageObj

        # Load Metas
        self['from'] = inlineDecoder(MessageObj['from'])
        self['to'] = inlineDecoder(MessageObj['to'])
        self['subject'] = inlineDecoder(MessageObj['subject'])
        self['content_charset'] = MessageObj.get_content_charset()
        self['content_type'] = MessageObj.get_content_type()
        self['content_maintype'] = MessageObj.get_content_maintype()
        self['content_subtype'] = MessageObj.get_content_subtype()
        self['is_multipart'] = MessageObj.is_multipart()
        self['filename'] = inlineDecoder(MessageObj.get_filename())

        # Load Children
        if self['is_multipart']:
            self['children'] = []
            for subMessage in MessageObj.get_payload():
                self['children'].append(MessageDecoded(subMessage))
            return
        
        # Load Content
        self['content'] = self['raw'] = MessageObj.get_payload(decode=True)
        if self['content_maintype'] == 'text':
            self['content'] = self['raw'].decode(self['content_charset'])

    def __getitem__(self,key):
        if key not in self.attrs:
            return None
        return self.attrs[key]
    
    def __setitem__(self,key,value):
        self.attrs[key] = value
    
    def keys(self):
        return self.attrs.keys()
    
    def items(self):
        return self.attrs.items()
    
    def values(self):
        return self.attrs.values()
    
    def __iter__(self):
        if self['is_multipart']:
            yield from self['children']
            return
        yield self

class MailReceiver:
    def __init__(self,host:str,port:int,SSL=True):
        self._host = host
        self._port = port
        self._ssl  = SSL
    
    def connect(self):
        clientClass = poplib.POP3_SSL if self._ssl else poplib.POP3
        self.client = clientClass(self._host,self._port)

    def login(self,user,pass_):
        self.client.user(user)
        self.client.pass_(pass_)

    def __len__(self):
        return len(self.client.list()[1])

    def __getitem__(self,index):
        if type(index) == int:
            return self.get(index,boundary_check=True)
        
        elif type(index) == slice:
            length = len(self)
            start = index.start or 0
            stop  = index.stop or length
            step  = index.step or 1
            if not (0 <= start <= stop <= length):
                raise IndexError('Index Out of Range [0,{0})'.format(length))
            def generator():
                for i in range(start,stop,step):
                    yield self.get(i,boundary_check=False)
            return generator()

    def get(self,index,boundary_check=True):
        if boundary_check:
            length = len(self)
            if not(0 <= index < length):
                raise IndexError('Index Out of Range [0,{0})'.format(length))
        binarySlices = self.client.retr(index+1)[1]
        binaryMessage = b'\r\n'.join(binarySlices)
        return MessageDecoded(bytesParser.parsebytes(binaryMessage))

    def __delitem__(self,index,boundary_check=True):
        if boundary_check:
            length = len(self)
            if not(0 <= index < length):
                raise IndexError('Index Out of Range [0,{0})'.format(length))
        self.client.dele(index+1)

    def __iter__(self):
        return self[:]

    def disconnect(self):
        self.client.quit()

class Text:
    def __init__(self,text,subtype='plain'):
        self.mime = MIMEText(text,subtype,'utf-8')

    def getMIME(self):
        return self.mime

class Binary:
    def __init__(self,byte,cid=None,filename=''):
        self.mime = MIMEApplication(byte)
        if filename!='':
            self.mime.add_header('Content-Disposition','attachment',filename=inlineEncoder(filename,'utf-8'))
        if cid != None:
            self.mime.add_header('Content-ID','{0}'.format(cid))
            self.mime.add_header('X-Attachment-Id','{0}'.format(cid))

    def getMIME(self):
        return self.mime

class Image:
    def __init__(self,byte,cid=None,filename=''):
        self.mime = MIMEImage(byte)
        if filename!='':
            self.mime.add_header('Content-Disposition','attachment',filename=inlineEncoder(filename,'utf-8'))
        if cid != None:
            self.mime.add_header('Content-ID','{0}'.format(cid))
            self.mime.add_header('X-Attachment-Id','{0}'.format(cid))

    def getMIME(self):
        return self.mime

class Container:
    def __init__(self,elements=None):
        self._elements = elements or []

    def add(self,element):
        self._elements.append(element)

    def getMIME(self):
        mime = MIMEMultipart()

        mime['From'] = inlineEncoder(self._fromName,'utf-8') + ' <{0}>'.format(self._from)
        mime['To'] = inlineEncoder('{0}'.format(self._toName),'utf-8')
        mime['Subject'] = inlineEncoder(self._subject,'utf-8')

        for el in self._elements:
            mime.attach(el.getMIME())

        return mime

class Envelop(Container):
    def __init__(self,from_:str,to,subject='',fromName='',toName='',elements=None):
        super().__init__(elements)
        
        self._from = from_
        self._to = to
        self._subject = subject

        self._toName = toName
        self._fromName = fromName

class MailSender:
    def __init__(self,host:str,port:int,SSL=True):
        self._host = host
        self._port = port
        self._ssl  = SSL

    def connect(self):
        clientClass = smtplib.SMTP_SSL if self._ssl else smtplib.SMTP
        self.client = clientClass(self._host,self._port)

    def login(self,user:str,pass_:str):
        self.client.login(user,pass_)

    def send(self,envelop:Envelop):
        _from = envelop._from
        _to   = envelop._to
        self.client.sendmail(_from,_to,envelop.getMIME().as_string())

    def disconnect(self):
        self.client.quit()


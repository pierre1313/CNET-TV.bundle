import datetime, re, pickle
from PMS import Plugin, Log, DB, Thread, XML, HTTP, JSON, RSS, Utils
from PMS.MediaXML import MediaContainer, DirectoryItem, VideoItem
from PMS.Shorthand import _L, _R, _E, _D

PLUGIN_PREFIX   = "/video/cnettv"
ROOT_URL        = "http://cnettv.cnet.com/"
TODAY_ON_CNET   = "videoId=50005295,50005285,50005271,50005283,50005297,50005280,50005263,50005291,50003920,50005185&rows=10&fl=title,lengthSecs,id,description,image,videoMedias,videoProfileId"
CNET_PARMS      = "&orderBy=productionDate~desc,createDate~desc&limit=20&iod=images,videoMedia,relatedLink,breadcrumb,relatedAssets,broadcast%2Clowcache&partTag=cntv&showBroadcast=true"
CNET_NAMESPACE  = {'l':'http://api.cnet.com/rest/v1.0/ns'}

####################################################################################################
def Start():
  Plugin.AddRequestHandler(PLUGIN_PREFIX, HandleVideosRequest, "CNET TV", "icon-default.png", "art-default.png")
  Plugin.AddViewGroup("Details", viewMode="InfoList", contentType="items")

def GetTodaysPlaylist(page):
  for script in page.xpath('//script'):
    if script.text:
      start = script.text.find('todaysPlaylist')
      if start != -1:
        matches = re.findall(r'[0-9,]+[0-9]+', script.text)
        if len(matches) > 0:
          return matches[0]
          
  return None

####################################################################################################
def HandleVideosRequest(pathNouns, count):
  dir = MediaContainer("art-default.png", None, "CNET TV")
  
  if count == 0:
    content = XML.ElementFromString(HTTP.GetCached(ROOT_URL), True)
    
    today = GetTodaysPlaylist(content)
    dir.AppendItem(DirectoryItem('Today/%s$%s$%s$%s' % ('videoId', today, 'CNET TV', _E('CNET Today')), 'Today on CNET', '', ''))
    
    for item in content.xpath('//ul[@id="mainMenu"]/li'):
      title = item.find('a').text_content()
      subMenus = []
      for subItem in item.xpath('ul/li/a'):
        try:
          onClickItems = [p.strip("'") for p in re.findall("'[^']+'", subItem.get('onclick'))]
          onClickItems[0] = onClickItems[0].replace(u'\x92',"'")
          subMenus += [onClickItems]
        except:
          pass
        
      if len(subMenus):
        sub = pickle.dumps(subMenus)
        dir.AppendItem(DirectoryItem(_E(sub) + '$' + title, title, '', ''))

  elif count == 1:
    (pickled, title) = pathNouns[0].split('$')
    dir.SetAttr("title2", title)
    
    subMenus = pickle.loads(_D(pickled))
    for menu in subMenus:
      dir.AppendItem(DirectoryItem(menu[1]+'$'+menu[2]+'$'+title+'$'+_E(menu[0].encode('utf-8')), unicode(menu[0]), '', ''))
  
  elif count == 2:
    (verb,params,title1,title2) = pathNouns[1].split('$')
    title2 = _D(title2)
    dir.SetAttr("title1", title1)
    dir.SetAttr("title2", title2)
    dir.SetViewGroup('Details')
    url = 'http://api.cnet.com/restApi/v1.0/videoSearch?' + verb.replace('videoId','videoIds').replace('node','categoryIds').replace('videoProfileIds', 'franchiseIds').replace('videoProfileId', 'franchiseIds') + '=' + params + CNET_PARMS
    
    data = HTTP.GetCached(url, 120, False)
    
    for video in XML.ElementFromString(data).xpath('//l:CNETResponse/l:Videos/l:Video', namespaces=CNET_NAMESPACE):
      summary = video.xpath('l:Description', namespaces=CNET_NAMESPACE)[0].text
      title = video.xpath('l:Title', namespaces=CNET_NAMESPACE)[0].text
      thumb = pickThumb(video.xpath('l:Images/l:Image', namespaces=CNET_NAMESPACE))
      duration = int(video.xpath('l:LengthSecs', namespaces=CNET_NAMESPACE)[0].text)*1000
      media = pickVideo(video.xpath('l:VideoMedias/l:VideoMedia', namespaces=CNET_NAMESPACE))
      if title.find(title2) == 0:
        title = title[len(title2)+2:]

      dir.AppendItem(VideoItem(media, title, summary, '%d' % duration, thumb))
    
  Plugin.Dict["CacheWorkaround"] = datetime.datetime.now()
  return dir.ToXML()

def pickVideo(videos):
  pickedBitrate = 0
  pickedURL = None
  for video in videos:
    bitrate = int(video.xpath('l:BitRate', namespaces=CNET_NAMESPACE)[0].text)
    if bitrate > pickedBitrate:
      pickedURL = video.xpath('l:DeliveryUrl', namespaces=CNET_NAMESPACE)[0].text
      pickedBitrate = bitrate
      
  return pickedURL
  
def pickThumb(images):
  pickedHeight = 0
  pickedThumb = None
  for image in images:
    height = int(image.get("height"))
    if height > pickedHeight:
      pickedThumb = image.xpath('l:ImageURL', namespaces=CNET_NAMESPACE)[0].text
      pickedHeight = height

  return pickedThumb
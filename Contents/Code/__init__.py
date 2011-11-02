import datetime, re

PLUGIN_PREFIX   = "/video/cnettv"
ROOT_URL        = "http://cnettv.cnet.com/"
SEARCH_API_URL  = "http://api.cnet.com/restApi/v1.0/videoSearch?%s=%s"
CNET_PARMS      = "&orderBy=productionDate~desc,createDate~desc&limit=20&iod=images,videoMedia,relatedLink,breadcrumb,relatedAssets,broadcast%2Clowcache&partTag=cntv&showBroadcast=true"
CNET_NAMESPACE  = {'l':'http://api.cnet.com/rest/v1.0/ns'}
PARAM_NAME_MAP  = {'videoId':'videoIds', 'node':'categoryIds', 'videoProfileIds':'franchiseIds', 'videoProfileId':'franchiseIds'}

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, "CNET TV", "icon-default.png", "art-default.jpg")
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  MediaContainer.art = R('art-default.jpg')
  MediaContainer.title1 ="CNET TV"
  DirectoryItem.thumb=R("icon-default.png")

#####################################  
def MainMenu():
  dir = MediaContainer() 
  videoId = TodaysVideoId()
  dir.Append(Function(DirectoryItem(Videos, title='Today on CNET'), key='videoIds', params=videoId))
  
  for item in HTML.ElementFromURL(ROOT_URL).xpath('//li[@class="expandable"]'):
    title = item.xpath('./a/text()')[0].strip()
    #Log(title)
    subMenus = []
    for subItem in item.xpath('.//nav/ul/li/a'):
      try:
        onClickItems = [p.strip("'") for p in re.findall("'[^']+'", subItem.get('onclick'))]
        onClickItems[0] = onClickItems[0].replace(u'\x92',"'")
        subMenus += [onClickItems]
      except:
        pass

    if len(subMenus) > 0:
      dir.Append(Function(DirectoryItem(Menu, title), subMenus=subMenus))

  return dir

#####################################
def Menu(sender, subMenus):
  dir = MediaContainer()

  for subMenu in subMenus:
    try:
      title = unicode(subMenu[0])
      key = PARAM_NAME_MAP[subMenu[1]]
      params = subMenu[2]
      dir.Append(Function(DirectoryItem(Videos, title), key=key, params=params))
    except:
      pass

  return dir

#####################################
def Videos(sender, key, params):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
  searchUrl = SEARCH_API_URL % (key, params) + CNET_PARMS

  for video in XML.ElementFromURL(searchUrl).xpath('//l:Videos/l:Video', namespaces=CNET_NAMESPACE):
    # Only process media items that have video
    if len(video.xpath('./l:VideoMedias', namespaces=CNET_NAMESPACE)) > 0:
      media = pickVideo(video.xpath('./l:VideoMedias/l:VideoMedia', namespaces=CNET_NAMESPACE))
      title = video.xpath('./l:Title', namespaces=CNET_NAMESPACE)[0].text
      summary = video.xpath('./l:Description', namespaces=CNET_NAMESPACE)[0].text
      thumb = pickThumb(video.xpath('./l:Images/l:Image', namespaces=CNET_NAMESPACE))
      duration = int(video.xpath('./l:LengthSecs', namespaces=CNET_NAMESPACE)[0].text)*1000
      subtitle = Datetime.ParseDate(video.xpath('./l:CreateDate', namespaces=CNET_NAMESPACE)[0].text).strftime('%a %b %d, %Y')
      if 'mp4 in media:
        dir.Append(VideoItem(media, title, subtitle=subtitle, summary=summary, duration=duration, thumb=thumb))

  return dir

#####################################
def TodaysVideoId():
  for script in HTML.ElementFromURL(ROOT_URL).xpath('//script'):
    if script.text != None:
      start = script.text.find('todaysPlaylist')
      if start != -1:
        matches = re.findall(r'[0-9,]+[0-9]+', script.text)
        if len(matches) > 0:
          videoId = matches[0]
          return videoId

  return None

###################################   
def pickVideo(videos):
  pickedBitrate = 0
  pickedURL = None
  for video in videos:
    bitrate = int(video.xpath('./l:BitRate', namespaces=CNET_NAMESPACE)[0].text)
    if bitrate > pickedBitrate:
      pickedURL = video.xpath('./l:DeliveryUrl', namespaces=CNET_NAMESPACE)[0].text
      pickedBitrate = bitrate

  return pickedURL

#######################################
def pickThumb(images):
  pickedHeight = 0
  pickedThumb = None
  for image in images:
    height = int(image.get("height"))
    if height > pickedHeight:
      pickedThumb = image.xpath('./l:ImageURL', namespaces=CNET_NAMESPACE)[0].text
      pickedHeight = height

  return pickedThumb

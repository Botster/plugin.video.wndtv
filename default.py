# Kodi Addon for WorldNetDaily

# Standard libraries
import sys, os, urllib, urllib2, urlparse, re, time
from HTMLParser import HTMLParser

# Kodi libraries
import xbmc, xbmcplugin, xbmcgui, xbmcaddon

# Identifiers
BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
addon         = xbmcaddon.Addon()
ADDON_NAME = addon.getAddonInfo('name')
home    = addon.getAddonInfo('path').decode('utf-8')
icon    = xbmc.translatePath(os.path.join(home, 'icon.png'))
fanart  = xbmc.translatePath(os.path.join(home, 'fanart.jpg'))

# Convenience
h = HTMLParser()
qp = urllib.quote_plus
uqp = urllib.unquote_plus

# Where the videos roam
DOMAIN_HOME = 'http://www.wnd.com/'
TV_PATH = 'wnd-tv/'


# -----------------
# --- Functions ---
# -----------------

# --- Helper functions ---

def log(txt, force=False):
    """
    Write text to Kodi log file.
    :param txt: text to write
    :type txt: str
    """
    message = '%s: %s' % (ADDON_NAME, txt.encode('ascii', 'ignore'))
    if force: xbmc.log(msg=message, level=xbmc.LOGERROR)
    else: xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def notify(message):
    """
    Execute built-in GUI Notification
    :param message: message to display
    :type message: str
    """
    command = 'XBMC.Notification("%s", "%s", %s)' % (ADDON_NAME, message , 5000)
    xbmc.executebuiltin(command)

def get_page(url):
    """
    Request a web page from url.
    :param url: Fully-qualified URL of resource
    :type url: str
    """
    log("get_page URL: %s" % url)

    user_agent = ['Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
                  'AppleWebKit/537.36 (KHTML, like Gecko)',
                  'Chrome/55.0.2883.87',
                  'Safari/537.36']
    user_agent = ' '.join(user_agent)
    headers = {'User-Agent':user_agent, 
               'Accept':"text/html", 
               'Accept-Language':'en-US,en;q=0.8'
                } 

    req = urllib2.Request(url.encode('utf-8'), None, headers)
    try:
        response = urllib2.urlopen(req)
        text = response.read()
        response.close()
    except (urllib2.URLError, AttributeError):
        notify('Cannot fetch %s' % url)
        text = None

    return(text)

# --- GUI director (Main Event) functions ---

def get_items(list_class, url=DOMAIN_HOME + TV_PATH):
    """ Accepts fully-qualified URL, retrieves list_class video item URLs  """
    
    if url is None: return # Cannot do anything

    ilist = []
    if list_class == 'slides':
        is_folder = False
        is_playable = True
        mode = 'play'
    else:
        is_folder = True
        is_playable = False
        mode = 'vids'
        liz = xbmcgui.ListItem('Breaking News', '', icon, None)
        newsurl = '%s?mode=%s&url=%s' % (BASE_URL, mode, qp(url))
        ilist.append((newsurl, liz, is_folder))
        
    regex_class = "tv-browse-" + list_class

    html = get_page(url)
    if html is None: return  # Sum Tin Wong
    match = re.search(r'<ul class="%s">(.*?)</ul>' % regex_class, html, re.DOTALL)
    if match:
        # Extract the <ul> section
        unordered_list = match.group(1)
        # Find all the anchor tags & flesh out infotags
        rx_url = r'href="(.*?)"'
        rx_img = r'data-bg-image="(.*?)"'
        rx_title = r'<h2 class="tv-browse-title">(.*?)</h2>'
        rx_subtitle = r'<p class="tv-browse-subtitle">(.*?)</p>'
        reg_exp = r'<a.+?%s.+?%s.+?%s.+?%s.+?</a>' % (rx_url, rx_img, rx_title, rx_subtitle)
        match = re.findall(reg_exp, unordered_list, re.DOTALL) 
        for url, img, title, subtitle in match:
            title = title.strip()
            subtitle = subtitle.strip()
            img = DOMAIN_HOME + img.lstrip('/')
            infoList = {}
            infoList['Title'] = subtitle
            url = '%s?mode=%s&url=%s' % (BASE_URL, mode, qp(url))
            liz=xbmcgui.ListItem(title)
            liz.setInfo( 'Video', infoList)
            liz.setArt({'thumb' : img, 'fanart' : img})
            if is_playable:
                liz.addStreamInfo('video', {'codec': 'h264'})
                liz.setProperty('IsPlayable', 'true')
            ilist.append((url, liz, is_folder))
                
        xbmcplugin.addDirectoryItems(ADDON_HANDLE, ilist, len(ilist))
        xbmcplugin.endOfDirectory(ADDON_HANDLE)

    else:
        notify("Error getting contents.")
        return

def get_video(url):
    """ Accepts fully-qualified URL, sets resolved URL on ListItem """

    # Retrieve page containing video address info
    page = get_page(url)
    
    # Parse for javascript playlist container
    # {"playlist":"http://content.jwplatform.com/jw6/4biLC13E.xml"}
    try:
        xml = re.search(r'\{.*?"playlist":"(.*?)"\}', page)
        xml = xml.group(1) # Reduce list to string

        # Retrieve XML playlist file
        playlist = get_page(xml)
        
        for source in re.findall(r'<jwplayer:source file="(.*?)"', playlist):
            url = source
            if 'token' in url: break
        else:
            url = False

    except  (AttributeError, TypeError):
        notify("Error retrieving video URL")
        return

    if not url: return
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, xbmcgui.ListItem(path=url))


# ------------------
# --- Main Event ---
# ------------------

# Parse query string into dictionary
try:
    params = urlparse.parse_qs(sys.argv[2][1:])
    for key in params:
        params[key] = params[key][0] # Reduce one-item list to string
        try: params[key] = uqp(params[key]).decode('utf-8')
        except: pass
except:
    params = {}

# What do to?
p = params.get

mode = p('mode', None)

if mode is None: get_items('grid')
elif mode=='vids':  get_items('slides', p('url', None))
elif mode=='play':  get_video(p('url', None))

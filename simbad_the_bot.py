from astroquery.simbad import Simbad
import astropy.coordinates as coord
import astropy.units as u
import aplpy
import requests
from PIL import Image,ImageFont,ImageDraw
import os
import glob
import images2gif
from urllib import urlencode
import tweepy
from random import randint,random

CONSUMER_KEY = '2iPGotHAeRq3tGXu0SakqhKaD'
CONSUMER_SECRET = 'VYiic0oDbh2W7xc0BVWM6MAeruMuXMZz7gIVZ6Nh2LaeW7hrSZ'
ACCESS_KEY = '745196439739981825-l4BLDWb7FwMQGuFHeHZqMBSl0omIgNO'
ACCESS_SECRET = 'zrkKt8eTjO91Adi8heo6NyODYmKjYuPiKGxTpTzUWOUET'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

greetings = ['Sail Ho!','Shiver me timbers!','Step To!','Splice the mainbrace!',\
			 'Anchors aweigh!','Batten down the hatches!','Blimey!',"Helm's a-lee!",\
			 'Hornswaggler!','Ahoy-hoy!','Fire in the hole!','Heave To!','Sink Me!',
			 'Avast ye!','Yo Ho Ho!','Blaggard!','Clear the bilges!']

font = ImageFont.truetype("Roboto-Bold.ttf",30)

more_url = "http://simbad.u-strasbg.fr/simbad/sim-basic?"
skyview_url = "http://skyview.gsfc.nasa.gov/cgi-bin/images"

skyview_params = {'pixels':'500,500','sampler':'Clip','size':'0.1,0.1',\
				  'projection':'Tan','coordinates':'J2000.0','return':'FITS'}

bands = {
		 'dss':(['dss2ir','dss2r','dss2b'],'Visible (DSS)'),\
		 'sdss':(['sdssi','sdssr','sdssg'],'Visible (SDSS)'),\
		 '2mass':(['2massk','2massh','2massj'],'Near-IR (2MASS)'),\
		 'wise':(['wisew4','wisew3','wisew2'],'Mid-IR (WISE)')\
		 }

customSimbad = Simbad()
customSimbad.add_votable_fields('otype(V)','coo(d)')

def get_random_object(max_star_fraction=0.2):
	"""
	Choose random RA/DEC and select nearest SIMBAD source, 
	biasing against boring-looking stars.
	Returns a human-readable txt string and object RA/DEC.
	"""
	coo = coord.SkyCoord(random()*360,random()*180-90,unit=(u.deg,u.deg))
	results = customSimbad.query_region(coo,radius=0.5*u.deg)
	for res in results:
		obj_name = ' '.join(res['MAIN_ID'].split())
		obj_type = res['OTYPE_V']
		if 'star' in obj_type.lower() and random() > max_star_fraction:
			continue
		a_an = 'an' if obj_type[0].upper() in ('X','A','E','I','O','U') else 'a'
		obj_coo = coord.SkyCoord(res['RA_d'],res['DEC_d'],unit=(u.deg,u.deg))
		constellation = coord.get_constellation(obj_coo)
		params = {'Ident':obj_name}
		greeting = greetings[randint(0,len(greetings)-1)]
		txt_str =  greeting + " %s is %s %s in the constellation %s. More: %s%s" % \
		(obj_name,a_an,obj_type,constellation,more_url,urlencode(params))
		
		return obj_name,txt_str,res['RA_d'],res['DEC_d']


def fetch_image(band,ra,dec,output):
	"""
	Fetch individual FITS image from SkyView and save to disk
	"""
	try:
		os.remove(output)
	except:
		pass
	skyview_params['position'] = "%s,%s" % (ra,dec)
	skyview_params['survey'] = band
	r = requests.get(skyview_url,params=skyview_params)
	if r.status_code == 200:
		with open(output, 'wb') as f:
			for chunk in r:
				f.write(chunk)


def create_rgb_image(survey,ra,dec):
	"""
	Fetch the three FITS images for the given survey and combine
	into an RGB png.
	"""
	try: os.remove(survey+'.png')
	except: pass	
	for i,band in enumerate(bands[survey][0]):
		fetch_image(band,ra,dec,output=survey+str(i)+'.fits')
	aplpy.make_rgb_image([survey+str(x)+'.fits' for x in range(3)],survey+'.png',\
			stretch_r='linear',stretch_g='linear',stretch_b='linear')


if __name__ == '__main__':
	obj_name,txt_str,ra,dec = get_random_object()
	print txt_str
	images = []
	for x in ['sdss','dss','2mass','wise']:
		try:
			create_rgb_image(x,ra,dec)
			im = Image.open(x+'.png')
			draw = ImageDraw.Draw(im)
			draw.text((20,20),bands[x][1],font=font)
			draw.text((20,450),obj_name,font=font)
			draw.line((150,250, 200,250), width=5)
			draw.line((250,150, 250,200), width=5)
			im.save(x+'.png')
			images.append(Image.open(x+'.png'))
		except:
			continue
	images2gif.writeGif('animation.gif',images,duration=2)

	try:
		api.update_with_media('animation.gif',txt_str)
	except:
		pass		






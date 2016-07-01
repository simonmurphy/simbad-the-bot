import os
import sys
from urllib import urlencode
from random import randint,random
from glob import glob
from datetime import datetime

import astropy.coordinates as coord
import aplpy
import requests
import images2gif
import tweepy
from astroquery.simbad import Simbad
from PIL import Image,ImageFont,ImageDraw

# Run a few times a day
when_to_run = [0, 6, 8, 16] 

pixel_size = 500,500 # px
image_size = 0.1,0.1 # deg

greetings = ['Sail Ho!','Shiver me timbers!','Step To!','Splice the mainbrace!',\
			 'Anchors aweigh!','Batten down the hatches!','Blimey!',"Helm's a-lee!",\
			 'Hornswaggler!','Ahoy-hoy!','Fire in the hole!','Heave To!','Sink Me!',
			 'Avast ye!','Yo Ho Ho!','Blaggard!','Clear the bilges!']

more_url    = "http://simbad.u-strasbg.fr/simbad/sim-basic?"
skyview_url = "http://skyview.gsfc.nasa.gov/cgi-bin/images"

skyview_params = {'pixels':'%s,%s'%pixel_size,\
				  'size':'%s,%s'%image_size,\
				  'sampler':'Clip','projection':'Tan',\
				  'coordinates':'J2000.0','return':'FITS'\
				  }

bands = {
		 '0_sdss':(['sdssi','sdssr','sdssg'],'Visible (SDSS)'),\
		 '1_dss':(['dss2ir','dss2r','dss2b'],'Visible (DSS)'),\
		 '2_2mass':(['2massk','2massh','2massj'],'Near-IR (2MASS)'),\
		 '3_wise':(['wisew4','wisew3','wisew2'],'Mid-IR (WISE)')\
		 }


def get_random_object(max_star_fraction=0.1):
	"""
	Choose random RA/DEC and select nearest SIMBAD source, 
	biasing against boring-looking stars.
	Returns a human-readable txt string and object RA/DEC.
	"""
	customSimbad = Simbad()
	customSimbad.add_votable_fields('otype(V)','coo(d)')

	coo = coord.SkyCoord(random()*360,random()*180-90,unit='deg')
	results = customSimbad.query_region(coo,radius='1 deg')
	
	for res in results:
		obj_name = ' '.join(res['MAIN_ID'].split())
		obj_type = res['OTYPE_V']
		if 'star' in obj_type.lower() and random() > max_star_fraction:
			continue
		a_an = 'an' if obj_type[0].upper() in ('X','A','E','I','O','U') else 'a'
		obj_coo = coord.SkyCoord(res['RA_d'],res['DEC_d'],unit='deg')		
		constellation = coord.get_constellation(obj_coo)
		greeting = greetings[randint(0,len(greetings)-1)]
		txt_str =  greeting + " %s is %s %s in the constellation %s. More: %s%s" % \
		(obj_name,a_an,obj_type,constellation,more_url,urlencode({'Ident':obj_name}))
		
		return obj_name,txt_str,res['RA_d'],res['DEC_d']


def fetch_image(band,ra,dec,output):
	"""
	Fetch individual FITS image from SkyView and save to disk
	"""
	skyview_params['position'] = "%s,%s" % (ra,dec)
	skyview_params['survey'] = band
	r = requests.get(skyview_url,params=skyview_params)
	if r.status_code == 200:
		with open(output, 'wb') as f:
			for chunk in r:
				f.write(chunk)
	else:
		raise Exception("Could not fetch image")


def create_rgb_image(survey,ra,dec):
	"""
	Fetch the three FITS images for the given survey and combine
	into an RGB png.
	"""
	for i,band in enumerate(bands[survey][0]):
		fetch_image(band,ra,dec,output=survey+str(i)+'.fits')
	aplpy.make_rgb_image([survey+str(x)+'.fits' for x in range(3)],survey+'.png',\
			stretch_r='linear',stretch_g='linear',stretch_b='linear')


def create_animation(images,obj_name):
	"""
	Annotate the colour images and combine into an animated GIF
	"""
	font = ImageFont.truetype("Roboto-Bold.ttf",30)
	frames = []
	for img in images:
		im = Image.open(img+'.png')
		draw = ImageDraw.Draw(im)
		draw.text((20,20),bands[img][1],font=font)
		draw.text((20,pixel_size[0]-50),obj_name,font=font)
		draw.line((pixel_size[0]/2-100,pixel_size[0]/2,pixel_size[0]/2-50, pixel_size[0]/2), width=5)
		draw.line((pixel_size[0]/2,pixel_size[0]/2-100, pixel_size[0]/2,pixel_size[0]/2-50), width=5)
		im.save(img+'.png')
		frames.append(Image.open(img+'.png'))

	images2gif.writeGif('animation.gif',frames,duration=2)



if __name__ == '__main__':

	# Heroku Scheduler runs every hour, so first
	# check if this is the right hour to run
	print datetime.today().hour,when_to_run
	if datetime.today().hour not in when_to_run:
		sys.exit(0)

	CONSUMER_KEY = os.environ['CONSUMER_KEY']
	CONSUMER_SECRET = os.environ['CONSUMER_SECRET']
	ACCESS_KEY = os.environ['ACCESS_KEY']
	ACCESS_SECRET = os.environ['ACCESS_SECRET']

	auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
	auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
	api = tweepy.API(auth)

	# Clean up
	files = glob("*.fits") + glob("*.png")
	for f in files:
		os.remove(f)
	
	images = []
	try:
		obj_name,txt_str,ra,dec = get_random_object(max_star_fraction=0.1)
		print txt_str
		print "RA,Dec:",ra,dec
		for survey in sorted(bands.keys()):
			try:
				# APLPy will choke on empty FITS files
				# from SkyView. Just skip them!
				create_rgb_image(survey,ra,dec)
				images.append(survey)
			except:
				pass
		create_animation(images,obj_name)
		# Send the tweet!
		api.update_with_media('animation.gif',txt_str)	
		print "Tweet sent."
		os._exit(0)
	except:
		# Die quietly and hope for better luck next time...
		print "Something went wrong."
		raise






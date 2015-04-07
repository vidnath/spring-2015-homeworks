#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import argparse
import logging
import requests
from BeautifulSoup import BeautifulSoup


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
loghandler = logging.StreamHandler(sys.stderr)
loghandler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
log.addHandler(loghandler)

base_url = "http://www.tripadvisor.com/"
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36"



def get_city_page(city, state, datadir):
    """ Returns the URL of the list of the hotels in a city. Corresponds to
    STEP 1 & 2 of the slides.
    Parameters
    ----------
    city : str
    state : str
    datadir : str
    Returns
    -------
    url : str
        The relative link to the website with the hotels list.
    """
    # Build the request URL
    url = base_url + "city=" + city + "&state=" + state
    # Request the HTML page
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers)
    html = response.text.encode('utf-8')
    with open(os.path.join(datadir, city + '-tourism-page.html'), "w") as h:
        h.write(html)

    # Use BeautifulSoup to extract the url for the list of hotels in
    # the city and state we are interested in.

    # For example in this case we need to get the following href
    # <li class="hotels twoLines">
    # <a href="/Hotels-g60745-Boston_Massachusetts-Hotels.html" data-trk="hotels_nav">...</a>
    soup = BeautifulSoup(html)
    li = soup.find("li", {"class": "hotels twoLines"})
    city_url = li.find('a', href=True)
    return city_url['href']


def get_hotellist_page(city_url, page_count, city, datadir='data/'):
    """ Returns the hotel list HTML. The URL of the list is the result of
    get_city_page(). Also, saves a copy of the HTML to the disk. Corresponds to
    STEP 3 of the slides.
    Parameters
    ----------
    city_url : str
        The relative URL of the hotels in the city we are interested in.
    page_count : int
        The page that we want to fetch. Used for keeping track of our progress.
    city : str
        The name of the city that we are interested in.
    datadir : str, default is 'data/'
        The directory in which to save the downloaded html.
    Returns
    -------
    html : str
        The HTML of the page with the list of the hotels.
    """

    url = base_url + city_url
    # Sleep 2 sec before starting a new http request
    time.sleep(2)
    # Request page
    headers = { 'User-Agent' : user_agent }
    response = requests.get(url, headers=headers)
    html = response.text.encode('utf-8')
    # Save the webpage
    with open(os.path.join(datadir, city + '-hotelist-' + str(page_count) + '.html'), "w") as h:
        h.write(html)
    return html


def parse_hotellist_page(html, hotels):
    """Parses the website with the hotel list and prints the hotel name, the
    number of stars and the number of reviews it has. If there is a next page
    in the hotel list, it returns a list to that page. Otherwise, it exits the
    script. Corresponds to STEP 4 of the slides.
    Parameters
    ----------
    html : str
        The HTML of the website with the hotel list.
    Returns
    -------
    URL : str
        If there is a next page, return a relative link to this page.
        Otherwise, exit the script.
    """
    soup = BeautifulSoup(html)
    # Extract hotel name, star rating and number of reviews
    hotel_boxes = soup.findAll('div', {'class' :'listing wrap reasoning_v5_wrap jfy_listing p13n_imperfect'})
    if not hotel_boxes:
        log.info("#################################### Option 2 ######################################")
        hotel_boxes = soup.findAll('div', {'class' :'listing_info jfy'})
    if not hotel_boxes:
        log.info("#################################### Option 3 ######################################")
        hotel_boxes = soup.findAll('div', {'class' :'listing easyClear  p13n_imperfect'})

    for hotel_box in hotel_boxes:
        hotel_name = hotel_box.find("a", {"target" : "_blank"}).find(text=True)
        log.info("Hotel name: %s" % hotel_name.strip())

        stars = hotel_box.find("img", {"class" : "sprite-ratings"})
        if stars:
            log.info("Stars: %s" % stars['alt'].split()[0])

        num_reviews = hotel_box.find("span", {'class': "more"}).findAll(text=True)
        if num_reviews:
            log.info("Number of reviews: %s " % [x for x in num_reviews if "review" in x][0].strip())

        #get URL of hotel page (like below)
        title_link = hotel_box.find("a", {"target" : "_blank"})['href']
        title_link = base_url + title_link
        hotel = parse_review(title_link, hotel_name)
        hotels[hotel_name] = hotel

    # Get next URL page if exists, otherwise exit
    div = soup.find("div", {"class" : "pagination paginationfillbtm"})
    #div is a nonetype
    # check if this is the last page
    if div.find("span", {"class" : "guiArw pageEndNext"}):
        log.info("We reached last page")
        return None
    # If not, return the url to the next page
    hrefs = div.findAll('a', href= True)
    for href in hrefs:
        if href.find(text = True).strip() == '&raquo;':
            log.info("Next url is %s" % href['href'])
            return href['href']

def parse_review(url, name):
    name={}
    #get HTML of the URL (like get_hotellist_page function)
    time.sleep(2)
    headers = { 'User-Agent' : user_agent }
    response = requests.get(url, headers=headers)
    html = response.text.encode('utf-8')
    #parse HTML to get REVIEW_FILTER_FORM like above
    soup = BeautifulSoup(html)
    databox = soup.find('div', {'class':'content wrap trip_type_layout'})
    #traveler ratings
    ratings = databox.findAll('div', {'class':'wrap row'})
    excellent = ratings[0]
    verygood = ratings[1]
    average = ratings[2]
    poor = ratings[3]
    terrible = ratings[4]
    rating_excellent = (excellent.find('span', {'class':'compositeCount'}).find(text=True)).strip().replace(",","")
    name['Excellent_ratings'] = rating_excellent
    rating_verygood = (verygood.find('span', {'class':'compositeCount'}).find(text=True)).strip().replace(",","")
    name['Verygood_ratings'] = rating_verygood
    rating_average = (average.find('span', {'class':'compositeCount'}).find(text=True)).strip().replace(",","")
    name['Average_ratings'] = rating_average
    rating_poor = (poor.find('span', {'class':'compositeCount'}).find(text=True)).strip().replace(",","")
    name['Poor_ratings'] = rating_poor
    rating_terrible = (terrible.find('span', {'class':'compositeCount'}).find(text=True)).strip().replace(",","")
    name['Terrible_ratings'] = rating_terrible
    avg_score = float(float(rating_excellent)*5 + float(rating_verygood)*4 + float(rating_average)*3 + float(rating_poor)*2 + float(rating_terrible)*1)/float(float(rating_excellent)+float(rating_verygood)+float(rating_average)+float(rating_poor)+float(rating_terrible))
    name['Average_score'] = avg_score
    #see reviews for different types of people
    peopletypes = databox.findAll('div', {'class':'filter_connection_wrapper'})
    families = peopletypes[0]
    couples = peopletypes[1]
    solo = peopletypes[2]
    business = peopletypes[3]
    f = (families.find('div', {'class':'value'}).find(text=True)).strip()
    name['Family_ratings'] = f
    c = (couples.find('div', {'class':'value'}).find(text=True)).strip()
    name['Couple_ratings'] = c
    s = (solo.find('div', {'class':'value'}).find(text=True)).strip()
    name['Solo_ratings'] = s
    b = (business.find('div', {'class':'value'}).find(text=True)).strip()
    name['Business_ratings'] = b
    #rating summary
    summaries = databox.findAll('li')
    sleep_quality = summaries[0].find('img')
    stars = sleep_quality['alt'].split(' ')[0]
    name['Sleep_quality'] = stars
    location = summaries[1].find('img')
    stars1 = location['alt'].split(' ')[0]
    name['Location']=stars1
    rooms = summaries[2].find('img')
    stars2 = location['alt'].split(' ')[0]
    name['Rooms']=stars2
    service = summaries[3].find('img')
    stars3 = location['alt'].split(' ')[0]
    name['Service']=stars3
    value = summaries[4].find('img')
    stars4 = value['alt'].split(' ')[0]
    name['Value']=stars4
    cleanliness = summaries[5].find('img')
    stars5 = cleanliness['alt'].split(' ')[0]
    name['Cleanliness']=stars5
    return name

def scrape_hotels_list(city,  state, datadir='data/'):
    """Produces a function which runs the webscraping on the hotels     on TripAdvisor

    Parameters
    ----------
    city : str
        The name of the city for which to scrape hotels.
    state : str
        The state in which the city is located.
    datadir : str, default is 'data/'
        The directory under which to save the downloaded html.
    """

    # Get current directory
    current_dir = os.getcwd()

    # Create datadir if does not exist
    if not os.path.exists(os.path.join(current_dir, datadir)):
        os.makedirs(os.path.join(current_dir, datadir))

    # Get URL to obtaint the list of hotels in a specific city
    city_url = get_city_page(city, state, datadir)

    hotel_dict={}

#    city_url = get_city_page(city, state, datadir)
#    html = hget_hotellist_page(city_url, 1, city, datadir)
#    city_url = parse_hotellist_page(html, hotel_dict)


#    for i in range(3):
#        html = hget_hotellist_page(city_url, i, city, datadir)
#        city_url = parse_hotellist_page(html, hotel_dict)

    # set a counter to contain number of iterations i.e. the
    # number of hotels
    count = 0

    # create a while loop to go through all of the hotel pages
    while(True):
        if count == 1: break

        count += 1
        html = get_hotellist_page(city_url, count, city, datadir)
        print '\n'
        city_url = parse_hotellist_page(html, hotel_dict)
        if city_url == None: break
    return hotel_dict


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape tripadvisor')
    parser.add_argument('-datadir', type=str,
                        help='Directory to store raw html files',
                        default="data/")
    parser.add_argument('-state', type=str,
                        help='State for which the hotel data is required.',
                        required=True)
    parser.add_argument('-city', type=str,
                        help='City for which the hotel data is required.',
                        required=True)

    args = parser.parse_args()
    scrape_hotels_list(args.city, args.state, args.datadir)

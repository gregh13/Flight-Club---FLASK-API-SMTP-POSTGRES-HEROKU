from urllib.error import HTTPError
from datetime import datetime, timedelta, date
from main import User, Preferences, FlightDeals, db
from new_iata_codes import all_cities_international
from bad_airlines import bad_airline_string
import requests
import base64
import urllib.parse
import random
import time


day_of_week = datetime.today().weekday()
MAIN_URL = "https://flightclubdeals.herokuapp.com/"
LOCATION_ENDPOINT = "https://tequila-api.kiwi.com/locations/query"
FLIGHT_ENDPOINT = "https://tequila-api.kiwi.com/v2/search"
FLIGHT_API_KEY = "Xr_BF4Uyg4T9g8Hiv75bVXbulMuIca9w"

GOAT_ACCESS_KEY = "e1d1a17cc2722373422ab8cbd9ec51ef"
GOAT_SECRET_KEY = "ab3b07cb5f9b54eb249b495d6da62e67"
headers = {
    "apikey": FLIGHT_API_KEY
}


def configure_flight_link(user_pref, flight_dict, total_passengers, bad_airline_string):

    flight_link_string = ""
    add_and_sign = True

    flight_link_string += f"https://www.kiwi.com/en/search/results/{flight_dict['airport_from_code']}/" \
                          f"{flight_dict['airport_to_code']}/{flight_dict['departure']}/" \
                          f"{flight_dict['leave_destination_date']}?"
    if user_pref['max_flight_time'] < 60:
        add_and_sign = False
        flight_link_string += f"flightDurationMax={user_pref['max_flight_time']}&"
    if user_pref["max_stops"] < 3:
        add_and_sign = False
        flight_link_string += f"stopNumber={user_pref['max_stops']}%7Etrue&"
    if user_pref['exclude_airlines'] == "true":
        add_and_sign = False
        flight_link_string += f"airlinesList={bad_airline_string.replace(',', '%2C')}&" \
                              f"selectedAirlinesExclude=true&"
    if add_and_sign:
        flight_link_string += "&"

    flight_link_string += f"sortBy=price"

    if user_pref['num_adults'] == 1 and total_passengers == 1:
        pass
    else:
        flight_link_string += f"&adults={user_pref['num_adults']}&" \
                              f"children={user_pref['num_children']}&" \
                              f"infants={user_pref['num_infants']}"
    if user_pref["cabin_class"] != "M":
        if user_pref["cabin_class"] == "W":
            flight_link_string += f"&cabinClass=PREMIUM_ECONOMY-true"
        if user_pref["cabin_class"] == "C":
            flight_link_string += f"&cabinClass=BUSINESS-true"
        if user_pref["cabin_class"] == "F":
            flight_link_string += f"&cabinClass=FIRST_CLASS-true"

    print(flight_link_string)

    return flight_link_string


def figure_out_dates(user_prefs):
    today = date.today()
    start_specific = user_prefs["specific_search_start_date"]
    end_specific = user_prefs["specific_search_end_date"]
    forward_start = (today + timedelta(days=user_prefs["search_start_date"])).strftime("%d/%m/%Y")
    forward_end = (today + timedelta(days=(user_prefs["search_start_date"] +
                                           user_prefs["search_length"]))).strftime("%d/%m/%Y")
    return_from = ""
    return_to = ""
    # Sets defaults, helps clean up 'if' statements below
    date_from = forward_start
    date_to = forward_end

    if start_specific:
        if end_specific:
            if start_specific >= today:
                # Start date is ok (and end date since validated with form)
                # Kiwi Flight Search requires dd/mm/yyyy format
                date_from = start_specific.strftime("%d/%m/%Y")
                date_to = end_specific.strftime("%d/%m/%Y")
                return_from = start_specific.strftime("%d/%m/%Y")
                return_to = end_specific.strftime("%d/%m/%Y")

            elif end_specific > (today + timedelta(days=(1 + user_prefs["min_nights"]))):
                # start date is past, check end date is ok
                date_from = today.strftime("%d/%m/%Y")
                date_to = end_specific.strftime("%d/%m/%Y")
                return_from = today.strftime("%d/%m/%Y")
                return_to = end_specific.strftime("%d/%m/%Y")

        elif start_specific >= today:
            # No end date, start date is okay (not past)
            date_from = start_specific.strftime("%d/%m/%Y")
            date_to = (start_specific + timedelta(days=user_prefs["search_length"])).strftime("%d/%m/%Y")

    elif end_specific:
        # Only end date
        if end_specific > (today + timedelta(days=(user_prefs["search_length"] + user_prefs["search_start_date"]))):
            # end date is okay (far enough out to cover search length), use lead time preference
            date_to = end_specific.strftime("%d/%m/%Y")
            return_from = forward_start
            return_to = end_specific.strftime("%d/%m/%Y")
        elif end_specific > (today + timedelta(days=(1 + user_prefs["min_nights"]))):
            # end date isn't far enough away to use lead time, use today for flight start
            date_from = today.strftime("%d/%m/%Y")
            date_to = end_specific.strftime("%d/%m/%Y")
            return_from = today.strftime("%d/%m/%Y")
            return_to = end_specific.strftime("%d/%m/%Y")

    date_dictionary = {"date_from": date_from, "date_to": date_to, "return_from": return_from, "return_to": return_to}

    return date_dictionary


def road_goat_image_search(city_name, country_to):
    def send_api_request(query):
        url = f"https://api.roadgoat.com/api/v2/destinations/auto_complete?q={query}"
        encoded_bytes = base64.b64encode(f'{GOAT_ACCESS_KEY}:{GOAT_SECRET_KEY}'.encode("utf-8"))
        auth_key = str(encoded_bytes, "utf-8")
        headers = {
            'Authorization': f'Basic {auth_key}'
        }
        response = requests.get(url=url, headers=headers)
        res = response.json()
        print("\nAutocomplete Data Results:")
        print(res)
        return res

    print(f"\nCountry: {country_to}\n")
    print(f"City Name: {city_name}")
    city_name = city_name.split(" - ")[0]
    url_encoded_city_name = urllib.parse.quote(city_name)
    url_encoded_country_name = urllib.parse.quote(country_to)

    results = send_api_request(query=url_encoded_city_name)
    if results["data"]:
        if results['data'][0]['relationships']['featured_photo']['data']:
            print(results["included"])
            image_link = results["included"][0]["attributes"]["image"]["full"]
        else:
            results = send_api_request(query=url_encoded_country_name)
            if results["data"]:
                if results['data'][0]['relationships']['featured_photo']['data']:
                    print(results["included"])
                    image_link = results["included"][0]["attributes"]["image"]["full"]
                else:
                    airplane = "https://images.pexels.com/photos/46148/aircraft-jet-landing-cloud-46148.jpeg?" \
                               "auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
                    image_link = airplane
            else:
                airplane = "https://images.pexels.com/photos/46148/aircraft-jet-landing-cloud-46148.jpeg?" \
                           "auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
                image_link = airplane
    else:
        results = send_api_request(query=url_encoded_country_name)
        if results["data"]:
            if results['data'][0]['relationships']['featured_photo']['data']:
                print(results["included"])
                image_link = results["included"][0]["attributes"]["image"]["full"]
            else:
                airplane = "https://images.pexels.com/photos/46148/aircraft-jet-landing-cloud-46148.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
                image_link = airplane
        else:
            airplane = "https://images.pexels.com/photos/46148/aircraft-jet-landing-cloud-46148.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
            image_link = airplane

    return image_link


def look_for_flights(user_prefs, destination):
    flight_date_dict = figure_out_dates(user_prefs)
    print(flight_date_dict)

    if user_prefs['exclude_airlines'] == "true":
        flight_parameters = {
            "fly_from": destination["home_airport"],
            "fly_to": destination["iata"],
            "date_from": flight_date_dict["date_from"],
            "date_to": flight_date_dict["date_to"],
            "return_from": flight_date_dict["return_from"],
            "return_to": flight_date_dict["return_to"],
            "nights_in_dst_from": user_prefs["min_nights"],
            "nights_in_dst_to": user_prefs["max_nights"],
            "flight_type": "round",
            "adults": user_prefs["num_adults"],
            "children": user_prefs["num_children"],
            "infants": user_prefs["num_infants"],
            "curr": destination["currency"],
            "selected_cabins": user_prefs["cabin_class"],
            "max_fly_duration": user_prefs["max_flight_time"],
            "max_sector_stopovers": user_prefs["max_stops"],
            "select_airlines": bad_airline_string,
            "select_airlines_exclude": "true",
            "limit": 1000
        }
    else:
        flight_parameters = {
            "fly_from": destination["home_airport"],
            "fly_to": destination["iata"],
            "date_from": flight_date_dict["date_from"],
            "date_to": flight_date_dict["date_to"],
            "nights_in_dst_from": user_prefs["min_nights"],
            "nights_in_dst_to": user_prefs["max_nights"],
            "flight_type": "round",
            "adults": user_prefs["num_adults"],
            "children": user_prefs["num_children"],
            "infants": user_prefs["num_infants"],
            "curr": destination["currency"],
            "selected_cabins": user_prefs["cabin_class"],
            "max_fly_duration": user_prefs["max_flight_time"],
            "max_sector_stopovers": user_prefs["max_stops"],
            "limit": 1000
        }
    print(flight_parameters)
    try:
        search_response = requests.get(url=FLIGHT_ENDPOINT, headers=headers, params=flight_parameters)
        # search_response.raise_for_status()
    except HTTPError:
        print("Home airport code is messed up")
        return
    else:
        return search_response.json()


def process_flight_info(flight_data):
    # Grabs first (cheapest) result
    data = flight_data["data"][0]
    # Sets default value in case 'if' statements don't get triggered
    leave_destination_date = data["route"][-1]['local_departure'].split("T")[0]
    # Catches more accurate departure date when return trip has multiple flights
    for route in data["route"]:
        if route["flyFrom"] == data['flyTo']:
            leave_destination_date = route['local_departure'].split("T")[0]
        if route["flyFrom"] == data["routes"][0][1]:
            leave_destination_date = route['local_departure'].split("T")[0]

    flight_data_dict = \
        {
            'city_from': data['cityFrom'],
            'airport_from_code': data['flyFrom'],
            'city_to': data['cityTo'],
            'airport_to_code': data['flyTo'],
            'country_to': data['countryTo']['name'],
            'departure': data['local_departure'].split("T")[0],
            'leave_destination_date': leave_destination_date,
            'arrival': data["route"][-1]['local_arrival'].split("T")[0],
            'nights_at_destination': int(data['nightsInDest']),
            'price': data['price'],
            'routes': data["routes"],
            "deep_link": data["deep_link"]
        }
    return flight_data_dict


def send_email(user_name, user_email, params: dict, template_id):
    url = "https://api.sendinblue.com/v3/smtp/email"
    payload = {
        "sender": {
            "email": "flightclubdeals@gmail.com",
            "name": "Flight Club"
        },
        "to": [{
            "email": user_email,
            "name": user_name
        }],
        "subject": "The results for your flight search are here!",
        "params": params,
        "templateId": template_id
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "api-key": "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"
    }
    response = requests.post(url, json=payload, headers=headers)
    print(response.text)
    return


# Grab data from database
all_users = User.query.all()
print(all_users)
for u in all_users:
    # # Helps slow down API calls to Tequila Kiwi Flight Search (100 requests per minute)
    # time.sleep(22)
    print(u.name)
    email_day = u.preferences[0].email_day
    if day_of_week != email_day:
        print("Not today, my friend!")
        continue
    user_preference_object = Preferences.query.filter_by(user_pref_id=u.preferences[0].user_pref_id).first()
    email_freq = user_preference_object.email_frequency
    # Find User Pref instead!!
    if email_freq != 1:
        if email_freq == 2:
            print("Biweekly, send")
            user_preference_object.email_frequency = 3
            db.session.commit()
        elif email_freq == 3:
            print("Biweekly, don't send")
            user_preference_object.email_frequency = 2
            db.session.commit()
            continue
        elif email_freq == 4:
            print("Monthly, send")
            user_preference_object.email_frequency = 5
            db.session.commit()
        elif email_freq == 5 or email_freq == 6:
            print("Monthly, don't send")
            user_preference_object.email_frequency = (email_freq + 1)
            db.session.commit()
            continue
        elif email_freq == 7:
            print("Monthly, don't send")
            user_preference_object.email_frequency = 4
            db.session.commit()
            continue

    bad_codes = []
    email_flight_deal_list = []
    website_flight_deal_dict = {"flight_search_date": date.today().strftime('%a, %B %-d, %Y')}
    for x in range(0, 10):
        website_flight_deal_dict[f"place{x + 1}"] = None
        website_flight_deal_dict[f"message{x + 1}"] = None
        website_flight_deal_dict[f"link{x + 1}"] = None
    user_name = u.name
    user_email = u.email
    print(f"{user_name}: {user_email}")

    user_preferences_dict = u.preferences[0].__dict__
    user_destinations_dict = u.destinations[0].__dict__
    # print(f'Preferences: {user_preferences_dict}')
    # print(f'Destinations: {user_destinations_dict}')

    total_passengers = (user_preferences_dict['num_adults']
                        + user_preferences_dict['num_children']
                        + user_preferences_dict['num_infants'])
    passengers = ""
    if user_preferences_dict['num_adults'] != 0:
        if user_preferences_dict['num_adults'] == 1:
            passengers += f"{user_preferences_dict['num_adults']} Adult"
        else:
            passengers += f"{user_preferences_dict['num_adults']} Adults"
    if user_preferences_dict['num_children'] != 0:
        if user_preferences_dict['num_children'] == 1:
            passengers += f", {user_preferences_dict['num_children']} Child"
        else:
            passengers += f", {user_preferences_dict['num_children']} Children"
    if user_preferences_dict['num_infants'] != 0:
        if user_preferences_dict['num_infants'] == 1:
            passengers += f", {user_preferences_dict['num_infants']} Infant"
        else:
            passengers += f", {user_preferences_dict['num_infants']} Infants"

    list_of_dicts = []
    for x in range(1, 11):
        dict_to_add = {"iata": user_destinations_dict[f'city{x}'],
                       "price_ceiling": user_destinations_dict[f'price{x}'],
                       "home_airport": user_destinations_dict["home_airport"],
                       "currency": user_destinations_dict["currency"]}
        if dict_to_add["iata"] is None:
            pass
        else:
            list_of_dicts.append(dict_to_add)

    for x in range(0, len(list_of_dicts)):
        destination = list_of_dicts[x]
        # 'Surprise Me' choice
        if destination["iata"] == "???":
            # While loop protects against randomly getting "???" again or same as home airport
            while destination["iata"] == "???" or destination["iata"] == user_destinations_dict["home_airport"]:
                destination["iata"] = random.choice(list(all_cities_international))

        city_name = all_cities_international[destination["iata"]]
        print(f"{city_name}: {destination['iata']}")
        flight_data = look_for_flights(user_prefs=user_preferences_dict, destination=destination)
        # When fly_to location code is bad or doesn't exist
        if 'Unprocessable Entity' in flight_data.values():
            print("BAD AIRPORT CODE\n")
            bad_codes.append(destination["iata"])
            message = "Error: Destination not recognized by flight search. Please change"
            website_flight_deal_dict[f"place{x + 1}"] = city_name
            website_flight_deal_dict[f"message{x + 1}"] = message
            # print(message)
            continue
        elif len(flight_data["data"]) == 0:
            print(f"No flight data for destination: {destination['iata']}\n")
            bad_codes.append(destination["iata"])
            message = "No flights available. Perhaps destination is too remote or quite far from your home airport " \
                      "(exceeds your max stops or flight duration), " \
                      "or perhaps travel restrictions are currently in place."
            website_flight_deal_dict[f"place{x + 1}"] = city_name
            website_flight_deal_dict[f"message{x + 1}"] = message
            # print(message)
            continue
        else:
            flight_dict = process_flight_info(flight_data=flight_data)
            # searched_currency = flight_data["currency"]
            # currency_rate_to_USD = flight_data["fx_rate"]
            price_ceiling = total_passengers * destination["price_ceiling"]

            if flight_dict["price"] <= price_ceiling:
                depart = datetime.strptime(flight_dict["departure"], '%Y-%m-%d')
                depart_day = depart.strftime('%A, %B %-d')
                back_home = datetime.strptime(flight_dict["arrival"], '%Y-%m-%d')
                back_home_day = back_home.strftime('%A, %B %-d')

                price_with_commas = "{:,}".format(flight_dict["price"])
                price_formatted = str(price_with_commas) + f" {destination['currency']}"
                image_link = road_goat_image_search(city_name=city_name, country_to=flight_dict["country_to"])

                # Catches cases where leaving airport and returning airport aren't the same (JFK to SFO, SFO to EWR)
                print(flight_dict["routes"])
                add_note = ""
                if flight_dict["routes"][0][0] == flight_dict["routes"][1][1]:
                    flight_link = configure_flight_link(user_pref=user_preferences_dict,
                                                        flight_dict=flight_dict,
                                                        total_passengers=total_passengers,
                                                        bad_airline_string=bad_airline_string)
                else:
                    add_note = f"Note: Leaving airport ({flight_dict['routes'][0][0]})" \
                               f" and returning airport ({flight_dict['routes'][1][1]}) are not the same"
                    flight_link = flight_dict["deep_link"]

                # flight_link = f"https://www.kiwi.com/en/search/results/{flight_dict['airport_from_code']}/" \
                #               f"{flight_dict['airport_to_code']}/{flight_dict['departure']}/" \
                #               f"{flight_dict['leave_destination_date']}?sortBy=price"
                email_flight_deal_list.append(
                    {
                        "city": flight_dict["city_to"],
                        "price": price_formatted,
                        "nights": flight_dict["nights_at_destination"],
                        "date1": depart_day,
                        "date2": back_home_day,
                        "image": image_link,
                        "num_passengers": total_passengers,
                        "passengers": passengers,
                        "link": flight_link
                    }
                )

                message = f"Deal Found! ${price_formatted} for {total_passengers} passengers ({passengers}) " \
                          f"from {depart_day} returning home on {back_home_day} " \
                          f"- ({flight_dict['nights_at_destination']} nights total)\n\n{add_note}"
                website_flight_deal_dict[f"place{x + 1}"] = city_name
                website_flight_deal_dict[f"message{x + 1}"] = message
                website_flight_deal_dict[f"link{x + 1}"] = flight_link
                # print(message)
                print(f"\nHomebrew Link: {flight_link}")
                print(f"\nDeep_link: {flight_dict['deep_link']}")
                print("\n")

            else:
                message = f"Flights available, but price wasn't lower than your limit " \
                          f"(${'{:,}'.format(destination['price_ceiling'])} {destination['currency']})"
                website_flight_deal_dict[f"place{x + 1}"] = city_name
                website_flight_deal_dict[f"message{x + 1}"] = message
                # print(message)

    FlightDeals.query.filter_by(user_deals_id=u.flight_deals[0].user_deals_id).update(website_flight_deal_dict)
    db.session.commit()

    if email_flight_deal_list:
        deals_found_params = {"destinations": email_flight_deal_list,
                              "header_link": MAIN_URL, "login_link": f"{MAIN_URL}login"}
        send_email(user_name=user_name,
                   user_email=user_email,
                   params=deals_found_params,
                   template_id=1)
        print("Flight Deal List:")
        print(email_flight_deal_list)
        print(f"\nNo flight info for: {bad_codes}")
    else:
        no_deals_params = {"login_link": f"{MAIN_URL}login", "header_link": MAIN_URL}
        send_email(user_name=user_name,
                   user_email=user_email,
                   params=no_deals_params,
                   template_id=3)
        print("No flight deals found this time around :(")
        print(f"\nNo flight info for: {bad_codes}")

    print("FINISHED")

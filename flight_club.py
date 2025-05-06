#This file will need to use the DataManager,FlightSearch, FlightData, NotificationManager classes to achieve the program requirements.
import requests
import datetime as dt
import time
import smtplib

API_KEY = "xCGw5NvlMPGQnsg6aSf1Wdum5n85N44q"
API_SECRET = "d86bOn4GzcjhMB1U"
SHEET_URL = "https://api.sheety.co/2231d296132c24d8aebae40d69be963e/copyOfFlightDeals/prices"
USERS_URL = "https://api.sheety.co/2231d296132c24d8aebae40d69be963e/copyOfFlightDeals/users"


class DataManager:
    #This class is responsible for talking to the Google Sheet.
    def __init__(self):
        self.des_data = []
        self.email_list = []

    def get_sheet_data(self):
        response1 = requests.get(url=SHEET_URL)
        data = response1.json()

        self.des_data = data['prices']
        return self.des_data

    def update_sheet_data(self):
        for city in self.des_data:
            data = {
                "price": {
                    "iataCode": city["iataCode"]
                }
            }
            response2 = requests.put(url=f"{SHEET_URL}/{city['id']}", json=data)

    def get_users(self):
        response5 = requests.get(url=USERS_URL)
        users_data = response5.json()

        for email in range(len(users_data["users"])):
            self.email_list.append(users_data["users"][email]["emailId"])

        return self.email_list


class FlightData:
    #This class is responsible for structuring the flight data.
    def __init__(self, price, ori_airport, des_airport, out_date, return_date, stops):
        self.price = price
        self.ori_airport = ori_airport
        self.des_airport = des_airport
        self.out_date = out_date
        self.return_date = return_date
        self.stops = stops


def find_cheapest_flight(data):

    if data is None or not data["data"]:
        return FlightData("N/A", "N/A", "N/A", "N/A", "N/A", "N/A")

    first_flight = data['data'][0]
    lowest_price = float(first_flight["price"]["grandTotal"])
    nr_stops = len(data["data"]["itineraries"][0]["segments"]) - 1
    origin = first_flight["itineraries"][0]["segments"][0]["departure"]["iataCode"]
    destination = first_flight["itineraries"][0]["segments"][0]["arrival"]["iataCode"]
    out_date = first_flight["itineraries"][0]["segments"][0]["departure"]["at"].split("T")[0]
    return_date = first_flight["itineraries"][1]["segments"][0]["departure"]["at"].split("T")[0]

    cheapest_flight = FlightData(lowest_price, origin, destination, out_date, return_date, nr_stops)

    for flight in data["data"]:
        price = float(flight["price"]["grandTotal"])
        if price < lowest_price:
            lowest_price = price
            origin = flight["itineraries"][0]["segments"][0]["departure"]["iataCode"]
            destination = flight["itineraries"][0]["segments"][0]["arrival"]["iataCode"]
            out_date = flight["itineraries"][0]["segments"][0]["departure"]["at"].split("T")[0]
            return_date = flight["itineraries"][1]["segments"][0]["departure"]["at"].split("T")[0]
            cheapest_flight = FlightData(lowest_price, origin, destination, out_date, return_date, nr_stops)
            print(f"Lowest price to {destination} is £{lowest_price}")

    return cheapest_flight


class FlightSearch:
    #This class is responsible for talking to the Flight Search API.
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = API_SECRET
        self.token = self.get_token()

    def get_token(self):
        headers = {
            "Content-type": "application/x-www-form-urlencoded"
        }

        body = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret
        }

        response1 = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token", headers=headers, data=body)
        return response1.json()['access_token']


    def check_iata_codes(self, city_name):
        parameters = {
            "keyword": city_name,
            "max": 2,
            "include": "AIRPORTS",
        }

        header = {
            "Authorization": f"Bearer {self.token}",
        }

        response2 = requests.get("https://test.api.amadeus.com/v1/reference-data/locations/cities", params=parameters, headers=header)
        try:
            code = response2.json()["data"][0]["iataCode"]
        except IndexError:
            return "N/A"
        except KeyError:
            return "N/A"

        return code

    def check_flight(self, ori_code, des_code, dep_date, return_date, adult, is_direct=True):
        headers = {
            "Authorization": f"Bearer {self.token}",
        }

        data = {
            "originLocationCode": ori_code,
            "destinationLocationCode": des_code,
            "departureDate": dep_date.strftime("%Y-%m-%d"),
            "returnDate": return_date.strftime("%Y-%m-%d"),
            "adults": adult,
            "nonStop": "true" if is_direct else "false",
            "currencyCode": "GBP",
        }

        response3 = requests.get("https://test.api.amadeus.com/v2/shopping/flight-offers", params=data, headers=headers)

        if response3.status_code != 200:
            return None

        return response3.json()


class NotificationManager:
    #This class is responsible for sending notifications with the deal flight details.
    def send_mail(self, email_list, message):
        with smtplib.SMTP("smtp.gmail.com") as connection:
            connection.starttls()
            connection.login(user="varunsvga@gmail.com", password="qmjb nllf kyep utgi")
            for email in email_list:
                connection.sendmail(from_addr="varunsvga@gmail.com",
                                    to_addrs= email,
                                    msg=message)


datamanager = DataManager()
sheet_data = datamanager.get_sheet_data()
flight_search = FlightSearch()
ori_code = "LON"

if sheet_data[0]["iataCode"] == "":
    for row in sheet_data:
        row["iataCode"] = flight_search.check_iata_codes(row["city"])
        time.sleep(2)

datamanager.update_sheet_data()

today = dt.datetime.now()
dep_date = today + dt.timedelta(days=1)
return_date = today + dt.timedelta(days=180)

email_list = datamanager.get_users()

for destination in sheet_data:
    print(f"Getting flights to {destination['city']}")
    flight = flight_search.check_flight(ori_code, destination["iataCode"], dep_date, return_date, 1)
    cheapest_flight = find_cheapest_flight(flight)
    time.sleep(2)

    if cheapest_flight.price == "N/A":
        print(f"No direct flights to {destination['city']}. Searching indirect flights...")
        stopover_flight = flight_search.check_flight(ori_code, destination['iataCode'], dep_date, return_date, 1, is_direct=False)
        cheapest_flight = find_cheapest_flight(stopover_flight)
        print(f"Cheapest indirect flight price is: £{cheapest_flight.price}")

    if cheapest_flight.price < destination["lowestPrice"]:
        print(f"Lower price flight found to {destination['city']}!")
        notmanager = NotificationManager()
        if cheapest_flight.stops == 0:
            notmanager.send_mail(email_list, f"Low price alert! Only £{cheapest_flight.price} to fly "
                          f"from {cheapest_flight.ori_airport} to {cheapest_flight.des_airport}, "
                          f"on {cheapest_flight.out_date} until {cheapest_flight.return_date}.")

        elif cheapest_flight.stops > 0:
            notmanager.send_mail(email_list, f"Low price alert! Only £{cheapest_flight.price} to fly "
                          f"from {cheapest_flight.ori_airport} to {cheapest_flight.des_airport}, "
                          f"with {cheapest_flight.stops} stops, "
                          f"on {cheapest_flight.out_date} until {cheapest_flight.return_date}.")

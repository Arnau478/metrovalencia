import time
import requests
import argparse
from unidecode import unidecode
import re

def edit_distance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

def line_color(n):
    # Official line colors
    if n == 1: return (0xE4, 0xBE, 0x36)
    if n == 2: return (0xB4, 0x39, 0x7F)
    if n == 3: return (0xB1, 0x1D, 0x2F)
    if n == 4: return (0x2B, 0x49, 0x8B)
    if n == 5: return (0x4E, 0x88, 0x6D)
    if n == 6: return (0x81, 0x7F, 0xB3)
    if n == 7: return (0xCE, 0x7D, 0x28)
    if n == 8: return (0x96, 0xC4, 0xDA)
    if n == 9: return (0xA4, 0x7E, 0x52)
    if n == 10: return (0xB6, 0xDD, 0x79)
    
    raise NotImplemented

def get_stations():
    stations_raw = requests.get("https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets/fgv-estacions-estaciones/exports/json?lang=es&timezone=Europe%2FBerlin").json()

    stations = {}
    for station in stations_raw:
        station_id = int(station['codigo'])
        stations[station_id] = {
            'id': station_id, 
            'name': station['nombre'],
            'lines': [int(x) for x in station['linea'].split(',')],
            'location': station['geo_shape']['geometry']['coordinates'][::-1]
        }

    return stations

def get_arrivals(id):
    response = requests.get(f"https://www.fgv.es/ap18/api/public/es/api/v1/V/horarios-prevision-3/{id}").json()
    
    arrivals = []
    for prevision in response["previsiones"]:
        for train in prevision["trains"]:
            arrivals.append({
                "line": prevision["line"],
                "destination": train["destino"],
                "arrival_time": train["seconds"]
            })

    return arrivals

def print_data(selected_station, format):
    arrivals = get_arrivals(selected_station)

    print(f"\x1b[1m{stations[selected_station]['name']}\x1b[0m", end="\n\n")

    for arrival in arrivals:
        color = line_color(arrival["line"])
        print(f"\x1b[38;2;255;255;255m\x1b[48;2;{color[0]};{color[1]};{color[2]}m {arrival['line']} \x1b[0m", end=" ")
        print(arrival["destination"], end=" "*max(1, 24-len(arrival["destination"])))
        
        arrival_time = arrival["arrival_time"]
        if format == "minutes":
            print(f"{round(arrival_time/60)} min")
        elif format == "seconds":
            print(f"{arrival_time}s")
        elif format == "mmss":
            print(f"{'0' if arrival_time//60 < 10 else ""}{arrival_time//60}:{'0' if arrival_time%60 < 10 else ""}{arrival_time%60}")
        else:
            raise NotImplemented

def normalize_name(name):
    name = name.casefold()
    name = unidecode(name)
    name = re.sub(r"[\-\/]", " ", name)
    name = re.sub(r" +", " ", name)
    name = name.strip(" ")
    return name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="metrovalencia",
        description="Get live data from metrovalencia",
    )
    parser.add_argument("station", help="The station name or internal ID")
    parser.add_argument("-f", "--format", choices=["minutes", "seconds", "mmss"], default="minutes", help="How the time of arrival will be formatted")
    parser.add_argument("-d", "--delay", default=15, help="Delay between requests")

    args = parser.parse_args()

    stations = get_stations()

    selected_station = None

    if args.station.isdigit():
        selected_station = int(args.station)
        if selected_station not in stations.keys():
            print(f"Invalid station ID: {selected_station}")
            exit()
    else:
        for i, station in stations.items():
            if normalize_name(station["name"]) == normalize_name(args.station):
                selected_station = i
        if selected_station is None:
            print(f"No station named \"{args.station}\"")
            best_match = min(stations.values(), key=lambda station: edit_distance(normalize_name(station["name"]), normalize_name(args.station)))
            if edit_distance(normalize_name(best_match["name"]), normalize_name(args.station)) < len(args.station)*0.75:
                print(f"Did you mean {best_match['name']}?")
            exit()

    while True:
        print("\x1b[H\x1b[J", end="")
        print_data(selected_station, args.format)
        time.sleep(args.delay)

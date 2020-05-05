import logging
from flask import jsonify
import localconfig as cfg
from forecastiopy import FIOHourly, ForecastIO


class Weather():
    # Defines possible weather strings from API to trigger on
    def __init__ (self):
        self._rain_types = {'Rain', 'Light Rain', 'Drizzle', 'Heavy Rain'}
        self._snow_types = {'Snow', 'Hail', 'Heavy Snow', 'Light Snow'}
        self._hourly_weather = None
        self._forecast_color = None

    def __repr__(self):
        return f'Weather({self._hourly_weather!r})'

    def get_weather(self):
        fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI,
                                    lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude=cfg.coordinates[0],
                                    longitude=cfg.coordinates[1])
        try:
            fio.has_hourly()
            self._hourly_weather = FIOHourly.FIOHourly(fio)
        except Exception:
            logging.error('No Hourly data')

    def print_weather_conditions(self):
        forecast = []
        for hour in range(0, 12):
            forecast.append(self._hourly_weather.get_hour(hour)["summary"])
        return forecast

    # Get weather forecast for next 12 hours and set lamp color to configured color if it will rain or snow
    def set_weather_color(self):
        for hour in range(0, 12):
            if self._hourly_weather.get_hour(hour)["summary"] in self._rain_types:
                self._forecast_color = cfg.rainColor
                break
            elif self._hourly_weather.get_hour(hour)["summary"] in self._snow_types:
                self._forecast_color = cfg.snowColor
                break
            else:
                logging.info(self._hourly_weather.get_hour(hour)["summary"])
                print(self._hourly_weather.get_hour(hour)["summary"])
            self._forecast_color = cfg.defaultColor
        return self._forecast_color

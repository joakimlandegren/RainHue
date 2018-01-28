import localconfig as cfg
from RainHue import get_weather_conditions_from_darksky, setLampColor
from flask import Flask, jsonify

# initiate api
app = Flask(__name__)

@app.route("/weather", methods=["GET"])
def return_weather_conditions():
    return jsonify(get_weather_conditions_from_darksky())

@app.route("/weather", methods=["POST"])
def set_lamp_color_to_weather():
    weather = get_weather_conditions_from_darksky()
    forecast = weather.pop()
    if forecast == "Rain":
        setLampColor(cfg.rainColor)
    elif forecast == "Snow":
        setLampColor(cfg.snowColor)
    else:
        setLampColor(cfg.defaultColor)
    return forecast

if __name__ == '__main__':
    app.run(port=5000, debug=True)
from flask import Flask, request as req
from flask_cors import CORS
from SPARQLWrapper import SPARQLWrapper, JSON
from classes.Request import Request

sparql = SPARQLWrapper("http://dbpedia.org/sparql")
sparql.setReturnFormat(JSON)

app = Flask(__name__)
cors = CORS(app)

types = {
    "artist": "dbo:MusicalArtist",
    "album": "dbo:Album"
    }

specs = ["name", "label"]

@app.route("/<string:type>/<string:spec>/<string:value>")
def get(type, spec, value):
    type = type.lower()
    spec = spec.lower()
    lang = req.args.get("lang") or "en"
    limit = req.args.get("limit") or "5"

    if type not in types.keys() or spec not in specs:
        return {}, 401
    if type == "album" and spec == "name":
        spec = "label"

    try:
        request = Request(sparql, types.get(type), spec, value, lang, int(limit))
        # print(request.request)
        results = request.send_request()
    except Exception as e:
        print(e)
        return str(e), 500

    # print(f"\n\nResults for query:\n{results}")
    return results, 200 if len(results.get("results")) != 0 else 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

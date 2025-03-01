from SPARQLWrapper import SPARQLWrapper, JSON
import requests

class Request():

    def __init__(self, wrapper: SPARQLWrapper, type: str, spec: str, value: str, extra_data: dict, lang: str = "en", limit: int = 5):
        self.wrapper = wrapper
        self.type = type
        self.spec = spec
        self.value = value
        self.query_type = extra_data.get("type")
        self.spec_type = extra_data.get("spec_type")
        self.prop_type = extra_data.get("prop_type")
        self.lang = lang
        self.limit = limit
        self.set_request()

    def __str__(self) -> str:
        return f"<Request  type={self.type}  spec={self.spec}  value={self.value}>"


    def set_request(self):
        extra_result_bindings = "" if self.type != "dbo:MusicalWork" else "dbo:artist ?artist; dbo:genre ?genre; "
        extra_bindings = "" if self.type != "dbo:MusicalWork" else "\n\t?artist rdf:type dbo:MusicalArtist; dbp:name ?artistName.\n\t?genre rdf:type dbo:Genre; dbp:name ?genreName."
        filters = f"\tFILTER(LANG(?name) = \"\" || LANG(?name) = \"{self.lang}\")\n\tFILTER(LANG(?abstract) = \"\" || LANG(?abstract) = \"{self.lang}\")\n"

        if self.query_type == "primary":
            result = f"?result rdf:type {self.type}; {extra_result_bindings}dbp:name ?name; dbo:abstract ?abstract.{extra_bindings}\n"
            inter = ""
            filters += f"\tFILTER (LCASE(STR(?{self.spec})) = LCASE(\"{self.value}\"))\n"
        else:
            result = f"?result rdf:type {self.type}; {extra_result_bindings}{self.prop_type} ?{self.spec}; dbp:name ?name; dbo:abstract ?abstract.{extra_bindings}\n"
            inter = f"?{self.spec} rdf:type {self.spec_type}; dbp:name ?{self.spec}Name.\n\t" if self.spec not in ["artist", "genre"] else ""
            filters += f"\tFILTER (LCASE(STR(?{self.spec}Name)) = LCASE(\"{self.value}\"))\n"

        self.request = f"SELECT * WHERE {{\n\t{inter}{result}{filters}}} LIMIT {min(100, self.limit * 3)}"


    def send_request(self) -> dict:
        self.wrapper.setQuery(self.request)
        results = self.wrapper.queryAndConvert()
        if len(results.get("results").get("bindings")) == 0:
            return {"results": []}
        results = results.get("results").get("bindings")
        inter_results = {
            "results": [
                {
                    "uri": result.get("result").get("value"),
                    "type": self.type,
                    "name": result.get("name").get("value"),
                    "abstract": result.get("abstract").get("value")
                } for result in results
            ]
        }
        if self.type == "dbo:MusicalWork":
            for i, result in enumerate(inter_results.get("results")):
                inter_results.get("results")[i]["musicGenreName"] = results[i].get("genreName").get("value")
                inter_results.get("results")[i]["musicArtistName"] = results[i].get("artistName").get("value")
                res = requests.get(f"https://musicbrainz.org/ws/2/recording?query=%22{result.get('name')}%22 AND artist:%22{result.get('musicArtistName')}%22&fmt=json").json()
                if res.get("recordings") is None or len(res.get("recordings")) == 0:
                    continue
                inter_results.get("results")[i]["musicLength"] = res.get("recordings")[0].get("length")

        if self.type != "dbo:MusicalWork":
            return inter_results

        musicGenres = {}
        for result in inter_results.get("results"):
            if result.get("name") not in musicGenres.keys():
                musicGenres[result.get("name")] = [result.get("musicGenreName")]
            else:
                musicGenres[result.get("name")].append(result.get("musicGenreName"))

        final_results = []

        for music, genres in musicGenres.items():
            new_result = [result for result in inter_results.get("results") if result.get("name") == music][0]
            new_result["musicGenreName"] = ', '.join(genres)
            final_results.append(new_result)

        return {"results": final_results[:self.limit]}

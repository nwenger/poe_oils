#!/usr/bin/python
"""
API for storing and retrieving data regarding POE Oils and anointments
"""
import json
import os
import urllib.request
import requests
import bs4

from flask import Flask, Response, jsonify
from flask_cors import CORS
from flask_restful import Resource, Api

#FIXME not sure if i need cors stuff still
#TODO decent handling of filepaths
#TODO determine worth of bs4
#TODO get rid of Recipe class
#TODO differentiate between ring and amulet recipes
#       and maps i think

OIL_WIKI='https://pathofexile.fandom.com/wiki/Oil#List_of_anointments'

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
api = Api(app)

def url_to_soup(url):
    """ convert url to beautiful soup. possibly unneeded """
    req = urllib.request.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
    html = urllib.request.urlopen(req).read()
    soup = bs4.BeautifulSoup(html, 'html.parser')
    return soup

class OilList(Resource):
    """ get or update list of oils """

    @staticmethod
    def update_oil_db(csv_path):
        """ truncate local oil list with content from wiki """
        soup = url_to_soup(OIL_WIKI)
        soup_oils = soup.find_all('span', attrs={'class':'c-item-hoverbox__activator'})
        oil_list = {}
        for oil in soup_oils:
            name = oil.find('a').getText()
            #/if not name.endswith('Oil') or name in oil_list.keys():
            if not name.endswith('Oil') or name in oil_list:
                continue
            image = oil.find('img').get('data-src')
            if image is not None:
                full_image = image[0:image.index('.png') + 4]
                data = requests.get(full_image, timeout=30).content
                filename = 'assets/' + name.replace(" ", "_") + ".png"
                with open(filename, "wb") as f:
                    f.write(data)
                oil_list[name] = filename
        with open(csv_path, "w+", encoding="utf-8") as f:
            for o in oil_list.items():
                f.write(o + '|' + oil_list[o] + "\n")

    def post(self):
        """ update local list of oils """
        self.update_oil_db('oil.list')
        return Response(200)

    @staticmethod
    def get():
        """ get array of oils in following json format
            {
                "name": "Something Oil",
                "image_src": "some/file/path.png"
            }
        """
        json_str = '{ "oils": ['
        with open('oil.list', "r", encoding="utf-8") as oils:
            for line in oils:
                fields = line.split('|')
                print(fields)
                json_str = json_str + '{"name":"' + fields[0] + \
                    '", "image_src":"' + fields[1].strip() + '"},'
        rv_json = json_str.rstrip(',') + ']}'
        response = jsonify(json.loads(rv_json))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response



class RecipeList(Resource):
    """ get or update POE oil recipes """

    class Recipe():
        """ structure for reorganizing anoint recipe into usable json """
        requires = []
        reward_name = ""
        reward_url = ""
        reward_details = ""

        def to_json_str(self):
            """ create json string for json.loads() """
            return '{ "requires": ' + str(self.requires).replace("'",'"') + \
                  ', "reward_name": "' + self.reward_name + \
                  '", "reward_src": "' + self.reward_url + \
                  '", "reward_details": "' + self.reward_details + '" }'

    def write_recipes(self, file, table):
        """ write anoint recipes from html table object to file """
        rows = table.find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            recipe_str = ''
            for col in columns:
                links = col.find_all('a')
                if len(links) == 0:
                    #is this always the last column?
                    recipe_str = recipe_str + col.getText() + '|'
                    continue
                for obj in links:
                    if len(obj.getText()) > 0:
                        recipe_str = recipe_str + obj.getText() + '|'
                    img = obj.find('img')
                    if img is not None:
                        data = requests.get(img.get('data-src'), timeout=30).content
                        filename = 'assets/' + col.getText().replace(" ", "_") + ".png"
                        with open(filename, "wb") as f:
                            f.write(data)
                        recipe_str = recipe_str + filename + '|'
            file.write(recipe_str.rstrip('|') + "\n")

    def update_recipe_db(self, csv_path):
        """ truncate local recipe.list with content from wiki """
        anoint_url = 'https://pathofexile.fandom.com/wiki/List_of_anointments'
        source = requests.get(anoint_url,timeout=30).text
        soup = bs4.BeautifulSoup(source, "lxml")
        tables = soup.find_all('table')
        with open(csv_path, "w+", encoding="utf-8") as f:
            for t in tables:
                self.write_recipes(f, t)

    def post(self):
        """ update local store of oil anointments """
        self.update_recipe_db('recipe.list')
        return Response(200)

    def get(self):
        """ get json of possible oil anointments in following format
        { "requires": ['Some Oil', 'Another Oil', 'More Oil']
          "reward_name": name of passive point
          "reward_src": path/to/image.png
          "reward_details": description of passive point
        """
        json_str = '{ "recipes": ['
        with open('recipe.list', "r", encoding="utf-8") as recipes:
            for line in recipes:
                if not line.strip():
                    continue
                fields = [ x.strip() for x in line.split('|')]
                field_len = len(fields)
                r = self.Recipe()
                if field_len == 6:
                    r.requires = [fields[0], fields[1], fields[2]]
                    r.reward_name = fields[3]
                    r.reward_url = fields[4]
                    r.reward_details = fields[5]
                #there is one exception that is missing details
                elif field_len == 5:
                    r.requires = [fields[0], fields[1], fields[2]]
                    r.reward_name = fields[3]
                    r.reward_url = fields[4]
                elif field_len == 4:
                    r.requires = [fields[0], fields[1]]
                    r.reward_name = ''
                    r.reward_url = ''
                    r.reward_details = fields[3]
                else:
                    print('Invalid field length: ')
                    print(fields)
                    continue
                json_str = json_str + r.to_json_str() + ','

        rv_json = json_str.rstrip(',') + ']}'
        response = jsonify(json.loads(rv_json))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response



api.add_resource(OilList, '/oils')
api.add_resource(RecipeList, '/recipes')

try:
    os.mkdir('assets/')
except FileExistsError:
    pass

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=9090)

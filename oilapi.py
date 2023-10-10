#!/usr/bin/python
import os
import urllib.request
import requests
import bs4
import json

from flask import Flask, request, Response, jsonify
from flask_cors import CORS, cross_origin
from flask_restful import Resource, Api

oil_wiki='https://pathofexile.fandom.com/wiki/Oil#List_of_anointments'
oil_output='oil.list'
recipe_output='recipe.list'

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
api = Api(app)

def url_to_soup(url):
	try:
		req = urllib.request.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
		html = urllib.request.urlopen(req).read()
		soup = bs4.BeautifulSoup(html, 'html.parser')
	except urllib.error.HTTPError:
		#try again if it fails to fetch
		time.sleep(5)
		req = urllib.request.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
		html = urllib.request.urlopen(req).read()
		soup = bs4.BeautifulSoup(html, 'html.parser')
	return soup

class OilList(Resource):

    @staticmethod
    def update_oil_db(csv_path):
        """ truncate local oil list with content from wiki """
        soup = url_to_soup(oil_wiki)
        soup_oils = soup.find_all('span', attrs={'class':'c-item-hoverbox__activator'})
        oil_list = {}
        for oil in soup_oils:
            name = oil.find('a').getText()
            if name in oil_list.keys() or not name.endswith('Oil'):
                continue
            image = oil.find('img').get('data-src')
            if image is not None:
                full_image = image[0:image.index('.png') + 4]
                data = requests.get(full_image).content
                filename = 'assets/' + name.replace(" ", "_") + ".png"
                with open(filename, "wb") as f:
                    f.write(data)
                oil_list[name] = filename
        with open(csv_path, "w+") as f:
            for o in oil_list:
                f.write(o + '|' + oil_list[o] + "\n")

    def post(self):
        self.update_oil_db('oil.list')
        return Response(200)

    @staticmethod
    def get():
        json_str = '{ "oils": ['
        with open('oil.list', "r") as oils:
            for line in oils:
                fields = line.split('|')
                print(fields)
                json_str = json_str + '{"name":"' + fields[0] + '", "image_src":"' + fields[1].strip() + '"},'
        rv_json = json_str.rstrip(',') + ']}'
        response = jsonify(json.loads(rv_json))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response



class RecipeList(Resource):

    class Recipe():
        requires = []
        reward_name = ""
        reward_url = ""
        reward_details = ""

        def to_json_str(self):
            return '{ "requires": ' + str(self.requires).replace("'",'"') + \
                  ', "reward_name": "' + self.reward_name + \
                  '", "reward_src": "' + self.reward_url + \
                  '", "reward_details": "' + self.reward_details + '" }'

    def write_recipes(self, file, table):
        rows = table.find_all('tr')
        for row in rows:
            recipe = self.Recipe()
            columns = row.find_all('td')
            recipe_str = ''
            last_col = ''
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
                        #TODO just download and save
                        data = requests.get(img.get('data-src')).content
                        filename = 'assets/' + col.getText().replace(" ", "_") + ".png"
                        with open(filename, "wb") as f:
                            f.write(data)
                        recipe_str = recipe_str + filename + '|'
            file.write(recipe_str.rstrip('|') + "\n")

    def update_recipe_db(self, csv_path):
        """ truncate local recipe.list with content from wiki """
        source = requests.get('https://pathofexile.fandom.com/wiki/List_of_anointments').text
        soup = bs4.BeautifulSoup(source, "lxml")
        tables = soup.find_all('table')
        with open(csv_path, "w+") as f:
            for t in tables:
                self.write_recipes(f, t)

    def post(self):
        self.update_recipe_db('recipe.list')
        return Response(200)

    def get(self):
        json_str = '{ "recipes": ['
        with open('recipe.list', "r") as recipes:
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

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=9090)

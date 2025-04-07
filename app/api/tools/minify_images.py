import os
import tinify

api_key = os.environ["TINIFY_API_KEY"]
tinify.key = api_key

path_source = 'app/api/static/stock-logos'
path_dest = 'app/api/static/stock-logos-minified'
files = os.listdir(path_source)
for file_name in files:
    file_path_source = f'{path_source}/{file_name}'
    file_path_dest = f'{path_dest}/{file_name}'

    source = tinify.from_file(file_path_source)
    source.to_file(file_path_dest)

#!/usr/bin/env python3
"""Choose the current route from requested editability, not a historical scenario."""
import argparse,json
from pathlib import Path

def decide(route,source_images,editable_data):
    if editable_data and route in ('image-deck','text-editable'):
        raise ValueError('Editable data objects require native; resolve the conflicting request')
    return route or ('text-editable' if source_images and not editable_data else 'native')
def main():
    p=argparse.ArgumentParser();p.add_argument('--route',choices=['native','image-deck','text-editable']);p.add_argument('--source-images',action='store_true');p.add_argument('--editable-data',action='store_true');p.add_argument('--out',type=Path);a=p.parse_args()
    try:route=decide(a.route,a.source_images,a.editable_data)
    except ValueError as e:p.error(str(e))
    text=json.dumps({'route':route,'alternate_required':False,'brand_policy':'selected template','backend':'current host contract'},indent=2)+'\n'
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text,encoding='utf-8')
    print(text,end='')
if __name__=='__main__':main()

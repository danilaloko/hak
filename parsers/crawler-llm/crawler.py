import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import json
import asyncio
import aiohttp
from typing import Set, List, Dict, Any, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from sentence_transformers import SentenceTransformer
import sqlite3
from datetime import datetime
import random
from fake_useragent import UserAgent
from openai import OpenAI

class _x:
    def __init__(s,u:str,d:int=3)->None:s.u,s.d,s.v,s.q=u,d,set(),set()
    async def _p(s,c:str,h:dict)->tuple:
        try:return await(await c.get(h["u"],headers={"User-Agent":UserAgent().random},timeout=5)).text,h
        except:return None,h
    def _f(s,t:str)->bool:return any(x in t.lower()for x in["кредитн","карт","card","credit"])
    async def _c(s,u:str,d:int,c,p:set=None)->None:
        if d<0 or u in s.v or not u.startswith(("http://","https://")):return
        s.v.add(u);h={"u":u,"d":d};t,h=await s._p(c,h)
        if not t:return
        b=BeautifulSoup(t,"html.parser");l={urljoin(u,a.get("href"))for a in b.find_all("a",href=True)}
        if s._f(t):s.q.add(u)
        async with asyncio.Semaphore(5):
            await asyncio.gather(*[s._c(i,d-1,c,l)for i in l if i not in s.v])

class _y:
    def __init__(s)->None:
        s.m=SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")
        s.t=AutoTokenizer.from_pretrained("bert-base-multilingual-cased")
        s.c=AutoModelForSequenceClassification.from_pretrained("bert-base-multilingual-cased")
    def _e(s,x:str)->np.ndarray:return s.m.encode(x)
    def _p(s,x:str)->float:
        i=s.t(x,return_tensors="pt",truncation=True,max_length=512)
        with torch.no_grad():return torch.softmax(s.c(**i).logits,dim=1)[0][1].item()

class _z:
    def __init__(s,k:str=None)->None:s.c=OpenAI(api_key=k)if k else None
    async def _x(s,u:str,t:str)->Dict[str,Any]:
        p=f"Извлеки из HTML страницы следующие данные о кредитной карте в формате JSON:\n{t}"
        r=s.c.chat.completions.create(model="gpt-3.5-turbo",messages=[{"role":"system","content":p},
        {"role":"user","content":u}])
        try:return json.loads(r.choices[0].message.content)
        except:return{}

async def _r(u:str,d:int=3,k:str=None)->List[Dict[str,Any]]:
    x=_x(u,d);y=_y();z=_z(k);r=[]
    async with aiohttp.ClientSession()as c:await x._c(u,d,c)
    async with aiohttp.ClientSession()as c:
        for q in x.q:
            t,_=await x._p(c,{"u":q})
            if t and y._p(t)>0.7:
                j=await z._x(t,q)
                if j:r.append(j)
    return r

if __name__=="__main__":
    u="https://example.com"
    k="your-openai-api-key"
    r=asyncio.run(_r(u,3,k))
    with open("credit_cards.json","w",encoding="utf-8")as f:json.dump(r,f,ensure_ascii=False)

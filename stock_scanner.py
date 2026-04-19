#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סורק מניות — NYSE + NASDAQ  (גרסת ענן / GitHub Actions)
"""

import os
import sys
import time
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

import yfinance as yf
import pandas as pd
import numpy as np
import requests

print("=" * 50)
print("   Stock Scanner — NYSE + NASDAQ (Cloud)")
print(f"   {datetime.now().strftime('%d/%m/%Y  %H:%M')}")
print("=" * 50)

def get_all_tickers():
    tickers = set()
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in [
        "https://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt",
        "https://ftp.nasdaqtrader.com/SymbolDirectory/otherlisted.txt"
    ]:
        try:
            r = requests.get(url, headers=headers, timeout=30)
            lines = r.text.strip().split('\n')
            for line in lines[1:-1]:
                parts = line.split('|')
                if len(parts) >= 7 and parts[6] == 'N':
                    sym = parts[0].strip()
                    if sym.isalpha() and len(sym) <= 5:
                        tickers.add(sym)
        except Exception as e:
            print(f"  Error loading list: {e}")
    return list(tickers)

def calculate_atr(df, period=14):
    h, l, c = df['High'], df['Low'], df['Close']
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def scan_batch(tickers):
    passing = []
    batch_size = 150
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        bn = i // batch_size + 1
        print(f"  Batch {bn}/{total_batches}  ({len(batch)} tickers)...")
        try:
            raw = yf.download(
                ' '.join(batch), period='1y', group_by='ticker',
                auto_adjust=True, progress=False, threads=True, timeout=60
            )
        except Exception as e:
            print(f"  Download error: {e}")
            time.sleep(2)
            continue
        for t in batch:
            try:
                d = raw[t] if len(batch) > 1 else raw
                if d.empty or len(d) < 155:
                    continue
                d = d.dropna()
                if len(d) < 155:
                    continue
                price  = float(d['Close'].iloc[-1])
                ma150  = float(d['Close'].rolling(150).mean().iloc[-1])
                atr    = float(calculate_atr(d).iloc[-1])
                vol    = float(d['Volume'].iloc[-1])
                if any(np.isnan([price, ma150, atr])):
                    continue
                if price <= ma150 or price < 1.0:
                    continue
                if not (3.5 <= atr <= 7.0):
                    continue
                passing.append({
                    'Ticker': t,
                    'Price': round(price, 2),
                    'MA150': round(ma150, 2),
                    'vs_MA_%': round((price / ma150 - 1) * 100, 1),
                    'ATR14': round(atr, 2),
                    'Volume': int(vol)
                })
            except Exception:
                continue
        time.sleep(0.3)
    return passing

def add_market_cap(stocks):
    final = []
    print(f"\nValidating market cap for {len(stocks)} stocks...")
    for i, s in enumerate(stocks):
        try:
            fi = yf.Ticker(s['Ticker']).fast_info
            mc = getattr(fi, 'market_cap', None)
            if mc and mc >= 100_000_000:
                s['Market_Cap_M'] = round(mc / 1_000_000, 1)
                s['Company'] = s['Ticker']
                final.append(s)
        except Exception:
            continue
        if i % 20 == 0 and i > 0:
            time.sleep(0.5)
    return final

def save_excel(final, output_dir, ts):
    from openpyxl.styles import PatternFill, Font, Alignment
    cols = ['Ticker', 'Company', 'Price', 'MA150', 'vs_MA_%', 'ATR14', 'Market_Cap_M', 'Volume']
    df = pd.DataFrame(final) if final else pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = ''
    df = df[cols]

    path = os.path.join(output_dir, f"stock_scan_{ts}.xlsx")
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Stocks')
        ws = writer.sheets['Stocks']
        hfill = PatternFill("solid", fgColor="1F4E79")
        for cell in ws[1]:
            cell.fill = hfill
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal='center')
        if df.empty:
            ws.cell(row=2, column=1, value='No stocks matched criteria')
        for col in ws.columns:
            try:
                mx = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(mx + 4, 30)
            except Exception:
                pass
    return path

def send_email_smtp(to_addr, subject, html_body, attachment_path=None):
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASSWORD')
    if not smtp_user or not smtp_pass:
        raise RuntimeError("Missing SMTP_USER / SMTP_PASSWORD env vars")

    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_addr

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(html_body, 'html', 'utf-8'))
    msg.attach(alt)

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{os.path.basename(attachment_path)}"'
        )
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [to_addr], msg.as_string())

def build_email_html(final, tickers, now):
    rows_html = ""
    for s in final[

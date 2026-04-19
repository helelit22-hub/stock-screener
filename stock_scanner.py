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
    for s in final[:30]:
        color = 'green' if s['vs_MA_%'] > 0 else 'red'
        rows_html += f"""<tr>
          <td style="padding:6px 10px;border:1px solid #ddd;font-weight:bold;color:#1F4E79">{s['Ticker']}</td>
          <td style="padding:6px 10px;border:1px solid #ddd">{s.get('Company','')[:30]}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:right">${s['Price']:.2f}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:right">${s['MA150']:.2f}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:right;color:{color}">{s['vs_MA_%']:+.1f}%</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:right;font-weight:bold">{s['ATR14']:.2f}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:right">${s.get('Market_Cap_M',0):,.0f}M</td>
        </tr>"""

    no_results = '<tr><td colspan="7" style="text-align:center;padding:20px;color:#999">No stocks found</td></tr>'
    return f"""
<div style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto" dir="rtl">
  <div style="background:#1F4E79;color:white;padding:20px;border-radius:8px 8px 0 0">
    <h2 style="margin:0">Stock Scan - Market Close</h2>
    <p style="margin:5px 0 0 0;opacity:0.85">{now.strftime('%A, %d/%m/%Y | %H:%M UTC')}</p>
  </div>
  <div style="padding:20px;background:white">
    <p>Scanned: {len(tickers):,} tickers | Passed filter: {len(final)}</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px" dir="ltr">
      <thead>
        <tr style="background:#1F4E79;color:white">
          <th style="padding:8px 10px;text-align:left">Ticker</th>
          <th style="padding:8px 10px;text-align:left">Company</th>
          <th style="padding:8px 10px;text-align:right">Price</th>
          <th style="padding:8px 10px;text-align:right">MA150</th>
          <th style="padding:8px 10px;text-align:right">% vs MA</th>
          <th style="padding:8px 10px;text-align:right">ATR14</th>
          <th style="padding:8px 10px;text-align:right">Market Cap</th>
        </tr>
      </thead>
      <tbody>{rows_html if rows_html else no_results}</tbody>
    </table>
  </div>
</div>"""

if __name__ == "__main__":
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    now = datetime.now()
    ts = now.strftime('%Y-%m-%d_%H%M')

    print("\nFetching tickers...")
    tickers = get_all_tickers()
    print(f"Total tickers: {len(tickers):,}")

    print("\nScanning price / MA150 / ATR...")
    preliminary = scan_batch(tickers)
    print(f"\nPassed price/ATR filter: {len(preliminary)} stocks")

    final = add_market_cap(preliminary)
    final.sort(key=lambda x: x['ATR14'], reverse=True)
    print(f"Passed market cap filter: {len(final)} stocks")

    print("\nSaving Excel...")
    xlsx_path = save_excel(final, OUTPUT_DIR, ts)
    print(f"Saved: {xlsx_path}")

    print("\nSending email...")
    to_addr = os.environ.get('MAIL_TO', '')
    subject = f"Stock Scan - Market Close | {now.strftime('%d/%m/%Y')}"
    html = build_email_html(final, tickers, now)
    try:
        send_email_smtp(to_addr, subject, html, attachment_path=xlsx_path)
        print(f"Email sent to {to_addr}")
    except Exception as e:
        print(f"Email error: {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print(f"   Done - {len(final)} stocks found")
    print("=" * 50)

# podcaster-boost-dashboard
Convert core-lightning's listinvoices output to a podcasting 2.0 dashboard

## Introduction

![screenshot](docs/image.png)

This is a simple Python script that converts core lightning's listinvoices output (which is a JSON file) into a podcasting 2.0 dashboard (static HTML+JavaScript).

See which episodes had boosts, what messages people left, etc.

## Usage

Use your core lightning's `lightning-cli listinvoices` output and feed it into this script.

An example for btcpayserver:

```bash
./bitcoin-lightning-cli.sh listinvoices > ~/invoices.json
# Optionally copy the invoices.json to your laptop and run the script there
python3 podcaster-boost-dashboard.py ~/invoices.json
```

(of course adjust the path to invoices.json).

Then open the resulting invoices.html (you can specify the name of the HTML file as second parameter, if you want) in a browser.


## Motivation

I have three podcasts, which all support value4value, but in order to see the boosts, I would have to either look manually at my node or use some custodial / third party service.

Since I want to operate a self-hosted, sovereign podcast, I wanted to create my own dashboard. I did not want to install anything on the node.


## Credits

Yes, I created this with ChatGPT-o1-preview, no shame, took me less than 20 minutes.

# --- START OF FINAL, CONFIGURABLE, AND SELF-DOCUMENTED CODE: pubchem_server.py ---

# Required imports
from typing import Any, List, Dict, Optional
import asyncio
import logging
import pubchempy as pcp
import json
import os
import requests
import time
import configparser

# --- 1. SCRIPT CONFIGURATION ---
# __file__ provides the script's path, os.path.realpath resolves it to an absolute path
# os.path.dirname gets the directory from that path.
SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# --- LOGGING CONFIGURATION ---
LOG_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, "logs_mcp")
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "mcp_debug.log")
os.makedirs(LOG_DIRECTORY, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE_PATH, filemode='w', force=True
)

# --- 2. READING AND CREATING THE CONFIGURATION FILE (config.ini) ---
config = configparser.ConfigParser()
CONFIG_FILE_PATH = os.path.join(SCRIPT_DIRECTORY, 'config.ini')

# Template for the default configuration file, with improved comments
DEFAULT_CONFIG_CONTENT = """
[proxy]
# Change 'use_proxy' to 'true' to route all requests through a proxy.
# Essential for protecting your privacy if you use Tor.
use_proxy = false

# Defines the proxy type to use. Options:
#   socks5h  -> (Recommended for Tor) The native SOCKS proxy for Tor. More secure.
#   http     -> An HTTP proxy. If using Tor, this requires additional configuration in your torrc.
proxy_type = socks5h

# The proxy address. THIS IS A CRITICAL SETTING!
#   - If you run this script on your DESKTOP (e.g., with AnythingLLM Desktop), use: 127.0.0.1
#   - If you run this script inside DOCKER (e.g., with AnythingLLM Docker), use: host.docker.internal
host = 127.0.0.1

# The proxy port.
#   9050 -> Default port for Tor's SOCKS proxy.
#   8118 -> Default port for Tor's HTTP proxy (if enabled).
port = 9050
"""

USE_PROXY = False
proxies = None
CONNECTION_TYPE = "Direct"

if not os.path.exists(CONFIG_FILE_PATH):
    logging.warning(f"config.ini not found. Creating a new one with default safe values.")
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        configfile.write(DEFAULT_CONFIG_CONTENT.strip())

config.read(CONFIG_FILE_PATH)
USE_PROXY = config.getboolean('proxy', 'use_proxy', fallback=False)

if USE_PROXY:
    proxy_type = config.get('proxy', 'proxy_type', fallback='socks5h').lower()
    proxy_host = config.get('proxy', 'host', fallback='127.0.0.1')
    proxy_port = config.getint('proxy', 'port', fallback=9050)
    
    if proxy_type not in ['socks5h', 'socks5', 'http', 'https']:
        logging.error(f"Invalid proxy_type '{proxy_type}' in config.ini. Defaulting to 'socks5h'.")
        proxy_type = 'socks5h'
        
    proxies = {
       'http': f'{proxy_type}://{proxy_host}:{proxy_port}',
       'https': f'{proxy_type}://{proxy_host}:{proxy_port}',
    }
    CONNECTION_TYPE = f"Proxy {proxy_type.upper()} ({proxies['https']})"
    logging.info(f"[{proxy_type.upper()} PROXY ENABLED] Will attempt to use proxy at {proxy_host}:{proxy_port}")
    
    try:
        response = requests.get("https://check.torproject.org/", proxies=proxies, timeout=30)
        response.raise_for_status()
        if "Congratulations. This browser is configured to use Tor." in response.text:
            logging.info(f"[{proxy_type.upper()} PROXY CHECK] SUCCESS! Connection through the Tor network verified successfully.")
        else:
            logging.warning(f"[{proxy_type.upper()} PROXY CHECK] WARNING: Connection was successful, but the response does not confirm Tor usage.")
    except requests.exceptions.RequestException as e:
        logging.critical(f"[{proxy_type.upper()} PROXY CHECK] !! CRITICAL FAILURE !! Could not connect through the proxy. Error: {e}")
        logging.critical(f"[{proxy_type.upper()} PROXY CHECK] Please ensure the proxy is running and that the required dependency (e.g., PySocks) is installed.")
else:
    logging.info("[PROXY DISABLED] Using a direct connection. Your real IP will be visible to PubChem.")

# MCP Server Initialization
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("pubchem")

# --- HELPER FUNCTIONS AND SEARCH LOGIC ---
def compound_to_dict(compound):
    """Safely converts a PubChemPy Compound object to a Python dictionary."""
    if not compound: return None
    try:
        props = compound.to_dict()
        keys_to_ensure = ["cid", "iupac_name", "molecular_formula", "molecular_weight", "monoisotopic_mass", "synonyms", "charge"]
        return {key: props.get(key) for key in keys_to_ensure}
    except Exception as e:
        logging.error(f"Could not convert compound to dictionary: {e}")
        return None

def search_by_name_with_retries(name: str, max_retries: int = 3, retry_delay: int = 5):
    """Searches for a compound using a fallback strategy (Compound -> Substance) and retries."""
    for attempt in range(max_retries):
        try:
            logging.info(f"Searching ({CONNECTION_TYPE}): '{name}' (Attempt {attempt + 1}/{max_retries})...")
            cid = None
            logging.info(f"   -> Attempt 1: Searching in 'Compound' domain")
            compounds = pcp.get_compounds(name, 'name', record_type='3d', max_records=1, proxies=proxies)
            if compounds and hasattr(compounds[0], 'cid') and compounds[0].cid:
                cid = compounds[0].cid
            if not cid:
                logging.warning(f"   -> Search in 'Compound' failed. Falling back to 'Substance' domain...")
                cids_from_substance = pcp.get_cids(name, 'name', 'substance', proxies=proxies)
                if cids_from_substance:
                    first_result = cids_from_substance[0]
                    if 'CID' in first_result and first_result['CID']:
                        cid = first_result['CID'][0]
            if not cid:
                logging.warning(f"No valid CID found for '{name}' in any domain.")
                return {"error": f"Compound '{name}' not found in PubChem.", "compound_name": name}
            logging.info(f"CID found for '{name}': {cid}. Fetching full record...")
            full_compound = pcp.Compound.from_cid(cid, proxies=proxies)
            result_dict = compound_to_dict(full_compound)
            if result_dict:
                result_dict['search_term'] = name
                return result_dict
            else:
                return {"error": f"Could not process full record for '{name}' (CID: {cid}).", "compound_name": name}
        except pcp.PubChemHTTPError as e:
            if 'Server Busy' in str(e) or '503' in str(e):
                logging.warning(f"Server busy for '{name}'. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            else:
                logging.error(f"PubChem HTTP Error for '{name}': {e}")
                return {"error": f"Compound '{name}' not found in PubChem (HTTP Error).", "compound_name": name}
        except Exception as e:
            logging.error(f"General error while searching for '{name}': {str(e)}")
            return {"error": f"General error for '{name}': {str(e)}", "compound_name": name}
    logging.error(f"Failed to search for '{name}' after {max_retries} attempts.")
    return {"error": f"Failed to get data for '{name}' after {max_retries} retries.", "compound_name": name}

def log_results_to_file(data):
    """Helper function to log results to the debug file."""
    logging.info("--- DEBUG: DATA BEING SENT TO LLM ---")
    results_as_json_string = json.dumps(data, indent=2)
    logging.info(results_as_json_string)
    logging.info("--- END OF DATA ---")

@mcp.tool()
async def search_compounds_by_name(names: List[str]) -> List[Dict[str, Any]]:
    """
    Searches for multiple compounds by name using a smart fallback strategy, one by one, with pauses and retries.
    Args:
        names: A list of compound names. Example: ["Aspirin", "Hydroxocobalamin"]
    """
    PAUSE_BETWEEN_REQUESTS = 2.0
    logging.info(f"Initiating SMART and SEQUENTIAL search for {len(names)} compounds...")
    all_results = []
    for name in names:
        result = await asyncio.to_thread(search_by_name_with_retries, name)
        all_results.append(result)
        logging.info(f"Pausing for {PAUSE_BETWEEN_REQUESTS}s.")
        await asyncio.sleep(PAUSE_BETWEEN_REQUESTS)
    log_results_to_file(all_results)
    return all_results

# --- ENTRY POINT ---
if __name__ == "__main__":
    logging.info("Starting PubChem MCP Server (final version, configurable and self-documented)")
    mcp.run(transport='stdio')
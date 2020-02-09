#!/usr/bin/env python3
"""
Script to log into the CloudGenix Controller UI and take screenshots.
Leverages Selenium-wire, headless Chrome, and CloudGenix SDK.
Also uses cloudgenix_config files as the data source.
"""
import sys
import os
import time
import yaml
import pathlib
import cloudgenix
from cloudgenix_config import config_lower_version_get
from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

# Default selenium items
DEFAULT_IMPLICIT_WAIT = 25  # seconds


# Create output function because print doesn't seem to flush enough
def ci_print(text, end="\n", color=None):
    red = '\033[0;31m'
    green = '\033[0;32m'
    yellow = '\033[1;33m'
    white = '\033[1;37m'
    nc = '\033[0m'

    if isinstance(color, str):
        if color.lower() == "red":
            output = red + text + end + nc
        elif color.lower() == "yellow":
            output = yellow + text + end + nc
        elif color.lower() == "green":
            output = green + text + end + nc
        elif color.lower() == "white":
            output = white + text + end + nc
        else:
            # unadded color
            output = text + end
    else:
        # not color name
        output = text + end
    sys.stdout.write(output)
    sys.stdout.flush()
    return


# Get CGX auth_token
if "AUTH_TOKEN" in os.environ:
    CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
else:
    # no AUTH_TOKEN
    ci_print("ERROR: No AUTH_TOKEN available for screenshots. Exiting.", color="red")
    sys.exit(1)

# For CI - get build info to link back to build logs.
if "TRAVIS_BUILD_NUMBER" in os.environ and "TRAVIS_BUILD_WEB_URL" in os.environ:
    # looks like Travis
    TRAVIS = True
    JENKINS = False
    CI_SYSTEM = "Travis CI"
    CI_COMMIT = os.environ.get("TRAVIS_COMMIT")
    CI_BUILD_ID = os.environ.get("TRAVIS_BUILD_NUMBER")
    CI_BUILD_URL = os.environ.get("TRAVIS_BUILD_WEB_URL")
elif "BUILD_ID" in os.environ and "BUILD_URL" in os.environ:
    # jenkins or compatible
    TRAVIS = False
    JENKINS = True
    CI_SYSTEM = "Jenkins"
    CI_COMMIT = os.environ.get("GIT_COMMIT")
    CI_BUILD_ID = os.environ.get("BUILD_NUMBER")
    CI_BUILD_URL = os.environ.get("BUILD_URL")
else:
    # no CI build info.
    TRAVIS = False
    JENKINS = False
    CI_SYSTEM = None
    CI_COMMIT = None
    CI_BUILD_ID = None
    CI_BUILD_URL = None


# Globals
UI_TOPOLOGY_PAGE = 'https://portal.{0}.cloudgenix.com/#map'
UI_SITE_PAGE = 'https://portal.{0}.cloudgenix.com/#map/site/{1}'
UI_ELEMENT_BASIC = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/basic_info'
UI_ELEMENT_TOOLKIT = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/device_toolkit'
UI_ELEMENT_INTERFACES = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/interfaces'
UI_ELEMENT_BGPPEERS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:peers'
UI_ELEMENT_BGPROUTEMAPS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:route_maps'
UI_ELEMENT_BGPPREFIXLISTS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:prefix_lists'
UI_ELEMENT_BGPASPATHACL = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:as_path_lists'
UI_ELEMENT_BGPIPCOMMUNITYLISTS = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/bgp:ip_community_lists'
UI_ELEMENT_STATICROUTES = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/routing/static_routes'
UI_ELEMENT_SNMP = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/snmp'
UI_ELEMENT_SYSLOG = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/syslog_export'
UI_ELEMENT_NTP = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/ntp_client'
UI_INTERFACES_DETAIL = 'https://portal.{0}.cloudgenix.com/#element/config/{1}/interfaces/{2}'

XPATH_1_INTERFACE_EXPANDS = "/html/body/div[1]/section/div/div[2]/div/div/div[2]/div/div/div[3]/div/div/form/" \
                            "div[2]/div/div/div[1]/a"
XPATH_2_INTERFACE_EXPANDS = "/html/body/div[1]/section/div/div[2]/div/div/div[2]/div/div/div[3]/div/div/form/" \
                            "div[3]/div/div/div[1]/a"
XPATH_CLOSE_WHATS_NEW = "/html/body/div[1]/div[4]/div/div/img"

FILENAME_VALID_CHARS = '-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def sanitize_filename(file_name):
    """
    Make sure a filename is only valid filename chars
    :param file_name: String to check
    :return: safer filename string
    """
    return ''.join(char for char in file_name if char in FILENAME_VALID_CHARS)


def is_int(val):
    """
    Check if value is able to be cast to int.
    :param val: String to be tested to int
    :return: Boolean, True if success
    """
    try:
        _ = int(val)
    except ValueError:
        return False
    return True


def screenshot_page(page_uri, sel_driver, output_filename, waitfor="time", waitfor_value="30", click_xpath=None,
                    click_xpath2=None, load_wait=15, load_tweak_delay=1):
    """
    Load and save a screnshot from the CGX UI
    :param page_uri: URI of page to get
    :param sel_driver: seleniumwire webdriver instance
    :param output_filename: Filename to save
    :param waitfor: Can be int (raw time), or id or class
    :param waitfor_value: ID or Class Name to wait for, if waitfor set to class or ID
    :param click_xpath: Optional - Full XPATH of element to load and click.
    :param click_xpath2: Optional - Second XPATH to load and click.
    :param load_wait: Default time for waitfor object to load.
    :param load_tweak_delay:
    :return:
    """

    # Time the screenshot.
    start = time.perf_counter()
    try:
        # Get page
        sel_driver.get(page_uri)
        # wait static or for id or class
        if isinstance(waitfor, str):
            if waitfor.lower() == 'class':
                _ = WebDriverWait(sel_driver, load_wait).until(
                    EC.presence_of_element_located((By.CLASS_NAME, waitfor_value)))
            elif waitfor.lower() == 'id':
                _ = WebDriverWait(sel_driver, load_wait).until(EC.presence_of_element_located((By.ID, waitfor_value)))
            elif waitfor.lower() == 'time':
                # check if can be cast to int:
                if is_int(waitfor_value):
                    # hard wait
                    time.sleep(int(waitfor_value))

            else:
                # invalid wait, just go
                pass

    except TimeoutException:
        ci_print("WARNING: Loading Page {0}, waiting for {1} '{2}' took longer than {3} seconds. "
                 "Saving data that exists."
                 "".format(page_uri, waitfor, waitfor_value, load_wait),
                 color="yellow")

    click_succeeded = 0
    click_requested = 0

    # For Find Element, it uses implicit wait. We want this to just try once. set to zero temporarily.
    driver.implicitly_wait(0)

    if click_xpath is not None:
        click_requested += 1
        # single click (not nec interface)
        try:
            click_dom = driver.find_elements_by_xpath(click_xpath)[0]
            click_dom.click()
            click_succeeded += 1
        except IndexError:
            # got a miss on the DOM select/click. Let's continue without the click.
            pass

    if click_xpath2 is not None:
        click_requested += 1
        # single click (not nec interface)
        try:
            click_dom = driver.find_elements_by_xpath(click_xpath2)[0]
            click_dom.click()
            click_succeeded += 1
        except IndexError:
            # got a miss on the DOM select/click. Let's continue without the click.
            pass

    if click_xpath or click_xpath2:
        # print status
        ci_print("Click({0} of {1} succeeded) ".format(click_succeeded, click_requested), end="")
    # set implicit wait back.
    driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)
    # Tweak delay
    time.sleep(load_tweak_delay)
    driver.get_screenshot_as_file(output_filename)
    # print the time
    stop = time.perf_counter()
    ci_print(f"(Elapsed {stop - start:0.4f}s): ", end="")
    return


# script start timer
script_start = time.perf_counter()

# quick check we have 1 argument.
if len(sys.argv) != 2:
    ci_print("ERROR: This script takes exactly 1 command line argument. Got the following: ", color="red")
    for arg in sys.argv:
        ci_print(arg, color="red")
    sys.exit(1)

# just one argument, it hopefully is the config file.
config_file = sys.argv[1]

# Try open config file, get list of site names, element names
try:
    with open(config_file, 'r') as datafile:
        loaded_config = yaml.safe_load(datafile)
except IOError as e:
    ci_print("ERROR: Could not open file {0}: {1}".format(config_file, e), color="red")
    sys.exit(1)

# let user know it worked.
ci_print("    Loaded Config File {0}.".format(config_file))

# create a site name-> ID dict and element name->ID dict.
sdk = cloudgenix.API()
sdk.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
region = sdk.controller_region
sites_n2id = sdk.build_lookup_dict(sdk.extract_items(sdk.get.sites()))
elements_n2id = sdk.build_lookup_dict(sdk.extract_items(sdk.get.elements()))

sites_dict = {}
config_sites, sites_api_version = config_lower_version_get(loaded_config, "sites", sdk.get.sites)
for site, config_site_cnf in config_sites.items():
    # get the list of element names
    elements_list = []
    config_elements, elements_api_version = config_lower_version_get(config_site_cnf, "elements", sdk.get.elements)
    for element, config_element_cnf in config_elements.items():
        elements_list.append(element)
    # update the sites dict with the site/element(s)
    sites_dict[site] = elements_list


# Create a new instance of the Chrome driver
# Headless mode of Chrome, ChromeDriver, and Selenium
options = webdriver.ChromeOptions()
options.add_argument('headless')
# long window, lots of room
options.add_argument('window-size=1920x1080')
driver = webdriver.Chrome(chrome_options=options)

# Interactive launch of the above, for debugging.
# driver = webdriver.Chrome()
# driver.set_window_size(1920, 1080)

# wait for DEFAULT_IMPLICIT_WAIT secs for all operations.
driver.implicitly_wait(DEFAULT_IMPLICIT_WAIT)
# default dom wait timer
delay = 20  # seconds
# default post dom wait timer
tweak_delay = 2  # seconds

# Set the request header using the `header_overrides` attribute
driver.header_overrides = {
    'X-Auth-Token': CLOUDGENIX_AUTH_TOKEN,
}

# start screenshot timer.
screenshot_start = time.perf_counter()

# Get map page to process and cache login
ci_print("    Logging in and taking topology screenshot: ", end="")
uri = UI_TOPOLOGY_PAGE.format(region)
filename = "screenshots/map.png"
# add a bit for tweak delay as tiles may take a while to load.
screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='leaflet-map-pane',
                click_xpath=XPATH_CLOSE_WHATS_NEW, load_tweak_delay=8)
ci_print("Done", color="green")

# Prep to generate markdown indexes
markdown_index = []

# start getting sites, elements, interfaces
for site_name, elements_list in sites_dict.items():
    site_id = sites_n2id.get(site_name)
    if site_id is None:
        # something wrong with this site. Print and continue.
        ci_print("WARNING: Could not get Site ID for Site {0}, skipping..".format(site_name), color="yellow")
        continue
    site_fs_name = sanitize_filename(site_name)
    site_directory = "screenshots/{0}/".format(site_fs_name)
    # make a directory
    pathlib.Path(site_directory).mkdir(parents=True, exist_ok=True)
    markdown_site_info = {
        "name": site_name,
        "fs_name": site_fs_name,
        "elements": []
    }

    # Get SITE page
    ci_print("    Taking Screenshot of Site '{0}' Site Map Card: ".format(site_name), end="")
    uri = UI_SITE_PAGE.format(region, site_id)
    filename = site_directory + "site-info.png"
    screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='site-info')
    ci_print("Done", color="green")

    for element_name in elements_list:
        element_id = elements_n2id.get(element_name)
        if element_id is None:
            # something wrong with this element. Print and continue.
            ci_print("WARNING: Could not get Element ID for Element {0}, skipping..".format(element_name),
                     color="yellow")
            continue
        element_fs_name = sanitize_filename(element_name)
        element_directory = site_directory + "{0}/".format(element_fs_name)
        pathlib.Path(element_directory).mkdir(parents=True, exist_ok=True)
        markdown_element_info = {
            "name": element_name,
            "fs_name": element_fs_name,
            "interfaces": []
        }

        # Get ELEMENT pages.
        # Note, static/bgp pages can get stuck, if we navigate to any other page after, it works fine.

        # Static Routes
        ci_print("      Taking Screenshot of Element '{0}' Static Routes: ".format(element_name), end="")
        uri = UI_ELEMENT_STATICROUTES.format(region, element_id)
        filename = element_directory + "static_routes.png"
        # first element item can take a bit while modal/backend stuff is cached. wait longer. Not needed mostly.
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='static-routing-table', load_wait=60)
        ci_print("Done", color="green")

        # Basic config
        ci_print("      Taking Screenshot of Element '{0}' Basic Config: ".format(element_name), end="")
        uri = UI_ELEMENT_BASIC.format(region, element_id)
        filename = element_directory + "basic_info.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='form-group')
        ci_print("Done", color="green")

        # BGP Peers table
        ci_print("      Taking Screenshot of Element '{0}' BGP Peers: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPPEERS.format(region, element_id)
        filename = element_directory + "bgp_peers.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='bgpPeersTable')
        ci_print("Done", color="green")

        # Device toolkit
        ci_print("      Taking Screenshot of Element '{0}' Device Toolkit: ".format(element_name), end="")
        uri = UI_ELEMENT_TOOLKIT.format(region, element_id)
        filename = element_directory + "device_toolkit.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='form-group')
        ci_print("Done", color="green")

        # BGP Route Maps
        ci_print("      Taking Screenshot of Element '{0}' BGP Route Maps: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPROUTEMAPS.format(region, element_id)
        filename = element_directory + "bgp_route_maps.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='routeMapsTable')
        ci_print("Done", color="green")

        # Interfaces summary
        ci_print("      Taking Screenshot of Element '{0}' Interfaces Summary: ".format(element_name), end="")
        uri = UI_ELEMENT_INTERFACES.format(region, element_id)
        filename = element_directory + "interfaces_summary.png"
        # bump window size up for Interfaces screen.
        driver.set_window_size(1920, 2160)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='interface_name-wrapper')
        # Set size back..
        driver.set_window_size(1920, 1080)
        ci_print("Done", color="green")

        # BGP Prefixlists
        ci_print("      Taking Screenshot of Element '{0}' BGP Prefix Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPPREFIXLISTS.format(region, element_id)
        filename = element_directory + "bgp_prefix_lists.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='prefixListsTable')
        ci_print("Done", color="green")

        # SNMP
        uri = UI_ELEMENT_SNMP.format(region, element_id)
        ci_print("      Taking Screenshot of Element '{0}' SNMP: ".format(element_name), end="")
        filename = element_directory + "snmp.png".format(site_name, element_name)
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='snmpAgentView')
        ci_print("Done", color="green")

        # BGP ASPATH ACL
        ci_print("      Taking Screenshot of Element '{0}' BGP AS-PATH Access Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPASPATHACL.format(region, element_id)
        filename = element_directory + "bgp_aspath_acl.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='asPathListsTable')
        ci_print("Done", color="green")

        # SYSLOG
        ci_print("      Taking Screenshot of Element '{0}' SYSLOG:  ".format(element_name), end="")
        uri = UI_ELEMENT_SYSLOG.format(region, element_id)
        filename = element_directory + "syslog.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='syslog-export-table')
        ci_print("Done", color="green")

        # BGP IP COMMUNITY Lists
        ci_print("      Taking Screenshot of Element '{0}' BGP IP Community Lists: ".format(element_name), end="")
        uri = UI_ELEMENT_BGPIPCOMMUNITYLISTS.format(region, element_id)
        filename = element_directory + "bgp_ip_community_lists.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='ipCommunityListsTable')
        ci_print("Done", color="green")

        # NTP
        ci_print("      Taking Screenshot of Element '{0}' NTP: ".format(element_name), end="")
        uri = UI_ELEMENT_NTP.format(region, element_id)
        filename = element_directory + "ntp.png"
        screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='ntp-servers-table')
        ci_print("Done", color="green")

        # get some interface screenshots.
        interfaces_unsorted = sdk.extract_items(sdk.get.interfaces(site_id, element_id))
        if len(interfaces_unsorted) >= 1:
            # sort the interfaces by name, for cleaner output
            interfaces_cache = sorted(interfaces_unsorted, key=lambda iface: iface['name'])
            # create interfaces directory, lets get some interface info.
            interface_directory = element_directory + "{0}/".format("interfaces")
            pathlib.Path(interface_directory).mkdir(parents=True, exist_ok=True)

            # bump window size up for Interfaces screen.
            driver.set_window_size(1920, 2160)

            for interface_record in interfaces_cache:
                interface_id = interface_record.get('id')
                interface_name = interface_record.get('name')
                interface_fs_name = sanitize_filename(interface_name)

                markdown_interface_info = {
                    "name": interface_name,
                    "fs_name": interface_fs_name
                }

                # interface get!
                ci_print("        Taking Screenshot of Interface '{0}' Configuration: ".format(interface_name), end="")
                uri = UI_INTERFACES_DETAIL.format(region, element_id, interface_id)
                filename = interface_directory + "{0}.png".format(interface_fs_name)
                screenshot_page(uri, driver, filename, waitfor="class", waitfor_value='collapsible-form__toggle',
                                click_xpath=XPATH_1_INTERFACE_EXPANDS, click_xpath2=XPATH_2_INTERFACE_EXPANDS)
                ci_print("Done", color="green")

                # save markdown info
                markdown_element_info["interfaces"].append(markdown_interface_info)

            # Set window size back..
            driver.set_window_size(1920, 1080)

        # save element markdown info
        markdown_site_info["elements"].append(markdown_element_info)

    # save site markdown info
    markdown_index.append(markdown_site_info)

# close the web page rendering engine
driver.close()
# save screenshot stop
screenshot_stop = time.perf_counter()

ci_print("    Creating changed item Markdown Indexes..", color="white")
# prep to generate markdown indexes.
for site in markdown_index:
    site_readme_filename = f"screenshots/{site['fs_name']}/README.md"
    site_readme_md = f"""\
## Site: {site['name']}{f'''

commit: {CI_COMMIT}''' if CI_COMMIT else ""}{f'''

{CI_SYSTEM} job id: [{CI_BUILD_ID}]({CI_BUILD_URL})''' if CI_SYSTEM else ""}

[Back To Topology](../README.md)
<img alt="Site Card" src="site-info.png?raw=1" width="1110">

### Elements
<ul>
"""

    for element in site['elements']:
        element_readme_filename = f"screenshots/{site['fs_name']}/{element['fs_name']}/README.md"
        element_readme_md = f"""\
## Element: {element['name']}{f'''

commit: {CI_COMMIT}''' if CI_COMMIT else ""}{f'''

{CI_SYSTEM} job id: [{CI_BUILD_ID}]({CI_BUILD_URL})''' if CI_SYSTEM else ""}

[Back To Site](../README.md)

### Interfaces
<ul>
<li>
<A href="interfaces/README.md">Interfaces Detail</A>
</li>
</ul>
<img alt="Interfaces Summary" src="interfaces_summary.png?raw=1" width="1110">

### Basic Info
<img alt="Basic Info" src="basic_info.png?raw=1" width="1110">

### Device Toolkit
<img alt="Device Toolkit" src="device_toolkit.png?raw=1" width="1110">

### Routing/BGP Peers
<img alt="BGP Peers" src="bgp_peers.png?raw=1" width="1110">

### Routing/BGP Route Maps
<img alt="BGP Route Maps" src="bgp_route_maps.png?raw=1" width="1110">

### Routing/BGP AS-Path Access Lists
<img alt="BGP Peers" src="bgp_aspath_acl.png?raw=1" width="1110">

### Routing/BGP Prefix Lists
<img alt="BGP Peers" src="bgp_prefix_lists.png?raw=1" width="1110">

### Routing/BGP Peers
<img alt="BGP Peers" src="bgp_ip_community_lists.png?raw=1" width="1110">

### Routing/Static
<img alt="Static Routes" src="static_routes.png?raw=1" width="1110">

### SNMP
<img alt="SNMP" src="snmp.png?raw=1" width="1110">

### SYSLOG
<img alt="SYSLOG" src="syslog.png?raw=1" width="1110">

### NTP
<img alt="NTP" src="ntp.png?raw=1" width="1110">

"""

        interface_readme_filename = f"screenshots/{site['fs_name']}/{element['fs_name']}/interfaces/README.md"
        # interface readme header
        interface_readme_md = f"""\
## Element: {element['name']} Interfaces{f'''

commit: {CI_COMMIT}''' if CI_COMMIT else ""}{f'''

{CI_SYSTEM} job id: [{CI_BUILD_ID}]({CI_BUILD_URL})''' if CI_SYSTEM else ""}

[Back To Element](../README.md)

"""

        # iterate interfaces
        for interface in element['interfaces']:
            # add individual interface info
            interface_readme_md += f"""\
### {interface['name']}
<img alt="1" src="{interface['fs_name']}.png?raw=1" width="1110">
                
"""

        # done with interfaces, write interface readme
        ci_print(f"      Writing {interface_readme_filename}: ", end="")
        with open(interface_readme_filename, 'w') as interface_readme_fd:
            interface_readme_fd.write(interface_readme_md)
        ci_print("Done", color="green")

        # also done with elements, as not any dynamic items
        ci_print(f"      Writing {element_readme_filename}: ", end="")
        with open(element_readme_filename, 'w') as element_readme_fd:
            element_readme_fd.write(element_readme_md)
        ci_print("Done", color="green")

        # update site readme MD with element info.
        site_readme_md += f"""\
<li>
<A href="{element['fs_name']}/README.md">{element['name']}</A>
</li>
"""

    # finish site readme md
    site_readme_md += """\
</ul>
"""

    ci_print(f"      Writing {site_readme_filename}: ", end="")
    with open(site_readme_filename, 'w') as site_readme_fd:
        site_readme_fd.write(site_readme_md)
    ci_print("Done", color="green")

# Script stop timer
script_stop = time.perf_counter()
ci_print(f"    File {config_file} completed. Screenshot time: {screenshot_stop - screenshot_start:0.4f}s, Total elapsed"
         f" time: {script_stop - script_start:0.4f}s")

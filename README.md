[![CloudGenix Logo](https://raw.githubusercontent.com/CloudGenix/network-as-code/master/scripts/images/CloudGenix_Logo.png)](https://www.cloudgenix.com)

[![Build Status](https://travis-ci.com/CloudGenix/network-as-code.svg?branch=master)](https://travis-ci.com/CloudGenix/network-as-code)
[![GitHub open pull requests](https://img.shields.io/github/issues-pr-raw/CloudGenix/network-as-code.svg)](https://github.com/CloudGenix/network-as-code/pulls)
[![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed-raw/CloudGenix/network-as-code?color=brightgreen)](https://github.com/CloudGenix/network-as-code/pulls?utf8=%E2%9C%93&q=is%3Apr+is%3Aclosed)
[![GitHub issues open](https://img.shields.io/github/issues/CloudGenix/network-as-code.svg)](https://github.com/CloudGenix/network-as-code/issues)
![GitHub License (MIT)](https://img.shields.io/github/license/CloudGenix/network-as-code?color=brightgreen)
# CloudGenix Network as Code Demo Environment
Demo of a CloudGenix Network as Code Environment

### Concept
Build an Enterprise-Class Remote Branch Office network using Coding tools and principles. Deploy, reconfigure at will.
All changes are tracked and approved using traditional Git-flow tools.

![Network as Code](https://raw.githubusercontent.com/CloudGenix/network-as-code/master/scripts/images/network-as-code.png)

Where is the source of truth that defines a network?
 - Traditional 'Router' Network: The source of truth is the "config file" on the Router.
 - SDN (Even SD-WAN) Network: The source of truth *should be* the configuration that lives on the controller (Isn't always - depends on vendor 😊.) 
 - DevOps Application Network, Network as Code: The source of truth is *wherever* and *whatever* you want it to be..

### Environment Overview

![Demo Overview](https://raw.githubusercontent.com/CloudGenix/network-as-code/master/scripts/images/Demo-Overview.png)

* Active CloudGenix Network
  * For this example, 3 sites, 6 devices. 
* GitHub Repository hosting the configurations for the network
  * Network change requests are `git pull` requests to the `master` branch
* Travis-ci set up to perform builds off `master` branch.
  * Once pulls are approved via GitHub process, code is automatically deployed into the network!
  * Successful deploys are tagged `in_prod` back in GitHub.
  * On failure can re-build, or check-in new changes to fix.
  * Logs and even CloudGenix UI screenshots are saved in the `results` branch.
  
### Tools Used
 - CloudGenix AppFabric SD-WAN Network - <https://www.cloudgenix.com>
 - CloudGenix Config CI/CD Utility - <https://github.com/CloudGenix/cloudgenix_config>
 - GitHub - <https://github.com>
 - Travis-ci - <https://travis-ci.com>

### Participate!
This demo isn't just for show. You too can make changes! To participate, do the following:
1. On your GitHub account, fork this repository. You've now got a copy of this repository you can change and edit! [![GitHub forks](https://img.shields.io/github/forks/CloudGenix/network-as-code?style=social)](https://github.com/CloudGenix/network-as-code/fork)
2. In the `configurations` directory, make some changes to one or more of the *.yml config files. You can do this right in GitHub by clicking "Edit File."
3. Commit your changes, give your commit a descriptive name. If using a local GIT repo, you need to push your commit back to your GitHub Fork.
4. Create a PULL request from your repository (and branch) to `CloudGenix/network-as-code:master`.  
3. The CloudGenix team will review and approve (or deny) your pull request, and then the change can be merged live.
4. After approval, changes should get made with the next run of Travis CI. 

To see your changes:
* Take a look at the [Build Logs](https://travis-ci.com/CloudGenix/network-as-code) 
* Or, see the [UI screenshots in the `results` branch](https://github.com/CloudGenix/network-as-code/tree/results/screenshots)!

For this demo, we'll attempt take most changes (within reason.) Even if stuff breaks, we can easily roll back.
For best/quickest results, here are the easiest changes to approve:
* Modify Descriptions, or Tags (Tags should be a YAML list of strings.)
* Modify names of stuff (site and non-servicelink interface names can't be changed.)
* Change DNS servers (Any well known public one should work.)

### Topology Detail

A diagram with more detail on the demo topology and port inter-connections:
![Topology Overview](https://raw.githubusercontent.com/CloudGenix/network-as-code/master/scripts/images/Topology-Overview.png)

### License
MIT




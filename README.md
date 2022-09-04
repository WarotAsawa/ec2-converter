
# ec2-converter
Simply convert VM List from CSV to cheapest ec2 instance type based on input requirement. Input example can be found on **example-source.csv** in this repository.

## How to install?
This script use python3 to run. Make sure you have python3 and PIP in your own machine.
You can use Git to clone this repository into your machine using below command. After that, go into the directory and run PIP to install required packages.

    git clone https://github.com/WarotAsawa/ec2-converter.git
    cd ./ec2-converter
    pip install -r requirements.txt

## How to use?
You can simply run **converter.py** in your CLI. The required option is the input file's (CSV) directory. The script will run and find the best choice of EC2 instance type on all row for you. This script will use **ec2-cost.csv** and **ec2-spec.csv** as its database to lookup all pricing. To update the database, you need to run **updateEC2Price.py** . The script will check if the output instance type in big enough for core, memory, GHz, IOPs, disk throughput and also check if the instance is available for input OS. Here is the example below

    python converter.py <input-file-name>.csv
After the script run successfully. The result will be output to CSV file with timestamp as 

    <input-fie-name>-result-<timestamp>.csv

Converter script has two option available.

 1. **include-prev** : Include previous EC@ generation in the output.
 2. **no-grav** : Exclude Gravitron instances in the output.

Here is the example to run with options

    python converter.py <input-file-name>.csv include-prev
    python converter.py <input-file-name>.csv no-grav
    python converter.py <input-file-name>.csv include-prev no-grav

## Updating price and spec database
If you need to keep the pricing up to date, simply run **updateEC2Price.py**. This script will get pricing from AWS Pricing API and  get EC2 specification from EC2 API using boto3 library. For this version, this update script is using the price from **ap-southeast-1 (Singapore)** region.

    python updateEC2Price.py

## Input File
You can put workload requirement as a row and as many as you like. Here is the definition of each column that you need to specify.

 - **Source Name** *(Required)* : Workload's Name
 - **Req Core** *(Required)* : Size of workload's CPU
 - **Req GHz** : Workload's Clock speed as GHz per Core
 - **Req Mem GB** *(Required)* : Size of workload's Memory as GB
 - **Req OS** *(Required)* : Workload's required OS. Available option is
		 - Linux
		 - Linux SQL Std
		 - Linux SQL Web
		 - Linux SQL Ent
		 - SLES
		 - Windows
		 - Windows SQL Std
		 - Windows SQL Web
		 - Windows SQL Ent
		 - RHEL
		 - RHEL SQL Std
		 - RHEL SQL Web
		 - RHEL SQL Ent
		 - RHEL HA
		 - RHEL HA SQL Std
		 - RHEL HA SQL Ent
 - **price-model** *(Required)* : Workload's pricing model as **on-demand** or **RIC-XY-XUF (reserved)**. Here is the options for reserved model:
		 - **RI/RIC: RI** for reserved instance, and **RIC** for convertible reserved instance
		 - **1Y/3Y:** 1-year or 3-year saving plan
		 - **NUF/PUF/AUF** : As for **N**o Upfront, **P**artial Upfront and **A**ll Upfront
 - **Req Disk GB** *(Required)* : Workload's storage size as in GB
 - **Req IOPs** : Workload's required disk IOPs
 - **Req MBps** : Workload's required disk throughput as in MBps
 - **Req BU Day** : Backup snapshot retention in days. This script will assume **1% data change daily.**

Here is the example of Input File **(example-source.csv)**
|Source Name |Req Core|Req GHz|Req Mem GB|Req OS |price-model|Req Disk GB|Req IOPs|Req MBps|Req BU Day|
|------------|--------|-------|----------|-------|-----------|-----------|--------|--------|----------|
|VM Source 01|1       |       |0.5       |Linux  |on-demand  |200        |3000    |125     |7         |
|VM Source 02|1       |       |0.5       |Windows|RI-1Y-NUF  |0.5        |100     |250     |7         |
|VM Source 03|2       |2.2    |4         |Windows|RI-1Y-PUF  |1000       |100000  |1000    |7         |
|VM Source 04|3       |       |6         |RHEL   |RI-1Y-AUF  |100        |100     |750     |7         |
|VM Source 05|4       |2.1    |4         |SLES   |RI-3Y-NUF  |20000      |3000    |1000    |7         |
|VM Source 06|1       |       |4         |Windows|RI-3Y-PUF  |100        |256000  |125     |14        |
|VM Source 07|2       |       |6         |Linux  |RI-3Y-AUF  |200        |3000    |250     |14        |
|VM Source 08|4       |       |8         |Linux  |RIC-1Y-NUF |0.5        |10000   |1000    |14        |
|VM Source 09|2       |       |10        |RHEL HA|RIC-1Y-PUF |0          |0       |0       |14        |
|VM Source 10|24      |       |1024      |SLES   |RIC-1Y-AUF |1500       |100     |1000    |14        |
|VM Source 11|32      |       |2048      |Windows|RIC-3Y-NUF |20000      |3000    |1000    |30        |
|VM Source 12|64      |       |2500      |Windows|RIC-3Y-PUF |100        |256000  |100     |30        |
|VM Source 13|100     |       |3000      |SLES   |RIC-3Y-AUF |20000      |1000    |50      |30        |

## Output File
THe output file will provide the most suitable for instance type based on your workload and script option with right EBS profile (GP3 or IO2). The output also provide the costing based on instance type, selected OS, selected saving plan, EBS' size, disk IOPs required, disk MBps required. Here is the output column listed as below.
 - **Instance Type** : The output's instance type
 - **vCPUs** : vCPU of instance type
 - **Mem GB** : Memory in GB of instance type
 - **EC2 Hourly** : The output's instance type's hourly pricing based on OS and saving plan
 - **EC2 Monthly** : The output's instance type's monthly pricing based on OS and saving plan
 - **EBS GB** : The sized of output EBS volume
 - **EBS Type** : The type of output EBS volume. Which can be either **GP3** or **IO2**
 - **EBSMonthly** : Monthly price of EBS storage volume
 - **BU GB** : Required backup storage based on EBS size and required snapshot retention.
 - **BU Monthly** : Monthly price of backup storage
 - **Total Monthly** : Sum of **EC2 Monthly**, **EBS Monthly** and **BU Monthly**

Here is the example of Output File **(example-source-result-[timestamp].csv)**
|Source Name|Req Core                     |Req GHz|Req Mem GB                                   |Req OS |price-model|Req Disk GB|Req IOPs|Req MBps|Req BU Day|Instance Type  |OS     |Pricing Model|vCPUs|Mem GB |EC2 Hourly         |EC2 Monthly       |EBS GB |EBS Type|EBS Monthly       |BU GB             |BU Monthly          |Total Monthly     |
|-----------|-----------------------------|-------|---------------------------------------------|-------|-----------|-----------|--------|--------|----------|---------------|-------|-------------|-----|-------|-------------------|------------------|-------|--------|------------------|------------------|--------------------|------------------|
|VM Source 01|1                            |       |0.5                                          |Linux  |on-demand  |200.0      |3000    |125     |7.0       |t3a.nano       |Linux  |on-demand    |2    |0.5    |0.0059             |4.306999999999999 |200.0  |GP3     |16.0              |214.0             |10.700000000000001  |31.006999999999998|
|VM Source 02|1                            |       |0.5                                          |Windows|RI-1Y-NUF  |0.5        |100     |250     |7.0       |t3a.nano       |Windows|RI-1Y-NUF    |2    |0.5    |0.0083             |6.059             |0.5    |GP3     |6.04              |0.535             |0.026750000000000003|12.12575          |
|VM Source 03|2                            |2.2    |4.0                                          |Windows|RI-1Y-PUF  |1000.0     |100000  |1000    |7.0       |c6i.24xlarge   |Windows|RI-1Y-PUF    |96   |192.0  |2.973557990867579  |2170.6973333333326|1000.0 |IO2     |7337.999999999999 |1070.0            |53.5                |9562.197333333332 |
|VM Source 04|3                            |       |6.0                                          |RHEL   |RI-1Y-AUF  |100.0      |100     |750     |7.0       |c6i.xlarge     |RHEL   |RI-1Y-AUF    |4    |8.0    |0.18139269406392602|132.416666666666  |100.0  |GP3     |38.0              |107.0             |5.35                |175.766666666666  |
|VM Source 05|4                            |2.1    |4.0                                          |SLES   |RI-3Y-NUF  |20000.0    |3000    |1000    |7.0       |c6i.xlarge     |SLES   |RI-3Y-NUF    |4    |8.0    |0.13391            |97.7543           |20000.0|IO2     |2976.0000000000005|21400.0           |1070.0              |4143.7543000000005|
|VM Source 06|1                            |       |4.0                                          |Windows|RI-3Y-PUF  |100.0      |256000  |125     |14.0      |x2idn.24xlarge |Windows|RI-3Y-PUF    |96   |1536.0 |4.308209589041096  |3144.993          |100.0  |IO2     |18445.8           |114.00000000000001|5.700000000000001   |21596.493         |
|VM Source 07|2                            |       |6.0                                          |Linux  |RI-3Y-AUF  |200.0      |3000    |250     |14.0      |t3a.large      |Linux  |RI-3Y-AUF    |2    |8.0    |0.034779299847793  |25.388888888888893|200.0  |GP3     |22.0              |228.00000000000003|11.400000000000002  |58.78888888888889 |
|VM Source 08|4                            |       |8.0                                          |Linux  |RIC-1Y-NUF |0.5        |10000   |1000    |14.0      |c6i.xlarge     |Linux  |RIC-1Y-NUF   |4    |8.0    |0.14877            |108.60210000000001|0.5    |GP3     |84.03999999999999 |0.5700000000000001|0.0285              |192.6706          |
|VM Source 09|2                            |       |10.0                                         |RHEL HA|RIC-1Y-PUF |0.0        |0       |0       |14.0      |r5a.large      |RHEL HA|RIC-1Y-PUF   |2    |16.0   |0.18603652968036502|135.80666666666647|0.0    |GP3     |0.0               |0.0               |0.0                 |135.80666666666647|
|VM Source 10|24                           |       |1024.0                                       |SLES   |RIC-1Y-AUF |1500.0     |100     |1000    |14.0      |r6i.metal      |SLES   |RIC-1Y-AUF   |128  |1024.0 |6.638013698630137  |4845.75           |1500.0 |GP3     |162.0             |1710.0000000000002|85.50000000000001   |5093.25           |
|VM Source 11|32                           |       |2048.0                                       |Windows|RIC-3Y-NUF |20000.0    |3000    |1000    |30.0      |x2iedn.16xlarge|Windows|RIC-3Y-NUF   |64   |2048.0 |10.40112           |7592.8176         |20000.0|IO2     |2976.0000000000005|26000.0           |1300.0              |11868.8176        |
|VM Source 12|64                           |       |2500.0                                       |Windows|RIC-3Y-PUF |100.0      |256000  |100     |30.0      |x2iedn.32xlarge|Windows|RIC-3Y-PUF   |128  |4096.0 |19.69748429223744  |14379.163533333332|100.0  |IO2     |18445.8           |130.0             |6.5                 |32831.46353333333 |
|VM Source 13|100                          |       |3000.0                                       |SLES   |RIC-3Y-AUF |20000.0    |1000    |50      |30.0      |x1e.32xlarge   |SLES   |RIC-3Y-AUF   |128  |3904.0 |13.004680365296805 |9493.416666666668 |20000.0|IO2     |2832.0000000000005|26000.0           |1300.0              |13625.416666666668|
|Total      |240                          |       |8615.0                                       |       |           |63201.0    |635300  |6650    |          |               |       |             |660  |12849.0|57.72215445966514  |42137.172755555555|63201.0|        |53341.67999999999 |76974.105         |3848.70525          |99327.55800555555 |


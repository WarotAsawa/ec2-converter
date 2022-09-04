import csv
import re
import re
from socket import IP_OPTIONS
import sys
import math
import json
import os
import pandas as pd
from datetime import datetime

def ImportDictFromCSV(filename):
    try:
        with open(filename, 'r',encoding='utf-8-sig') as read_obj:
            # pass the file object to DictReader() to get the DictReader object
            dict_reader = csv.DictReader(read_obj)
            # get a list of dictionaries from dct_reader
            list_of_dict = list(dict_reader)
            # print list of dict i.e. rows
            return list_of_dict
    except:
        return "ERROR"

def GetInstanceTypeSpecObj(ec2Type, ec2Spec):
    for item in ec2Spec:
        if item['instanceType'] == ec2Type:
            return item
    
def GetLowestInstancePrice(input, ec2Cost, ec2Spec, options):
    minCost = 999999.9
    cpu = 0
    ghz = 0
    memory = 0
    reqDiskGB = 0
    reqDiskIOPs = 0
    reqDiskThroughput = 0
    reqBUDay = 0
    priceModel = 'on-demand'
    os = "Linux"
    if input['Req Core']    != "": cpu = int(input['Req Core'])
    if input['Req GHz']     != "": ghz = float(input['Req GHz'])
    if input['Req Mem GB']  != "": memory = float(input['Req Mem GB'])
    if input['Req OS']  != "": os = input['Req OS']
    if input['price-model'] != '': priceModel = input['price-model'] 
    if input['Req Disk GB']    != "": reqDiskGB = float(input['Req Disk GB'])
    if input['Req IOPs']    != "": reqDiskIOPs = float(input['Req IOPs'])
    if input['Req MBps']    != "": reqDiskThroughput = float(input['Req MBps'])
    if input['Req BU Day']    != "": reqBUDay = float(input['Req BU Day'])

    print(input["Source Name"] + " : " + str(cpu) + " cores, " + str(ghz) + " GHz, " + str(memory) + " GB mem, " + os + " OS")
    #Cap Disk Size and IOPs MBps
    if reqDiskGB > 64000: reqDiskGB = 64000
    if reqDiskIOPs > 256000 : reqDiskIOPs = 256000
    if reqDiskThroughput > 4000 : reqDiskThroughput = 4000
    #Set Options
    noGrav = False
    includePrev = False
    for opt in options:
        if "no-grav" in opt: noGrav = True
        if "include-prev" in opt: includePrev = True
    for ec2Type in ec2Cost:
        #print(ec2Type)
        spec = GetInstanceTypeSpecObj(ec2Type["API Name"], ec2Spec)
        try: specGHz = float(spec['clockSpeed'].split(' ')[0])
        except: specGHz = 0.1
        specCPU = float(spec['vcpu'].split(' ')[0])
        specMem = float(spec['memory'].split(' ')[0])
        #Logic is here
        model = os + "-" + priceModel
        #Skip if resource if not enough
        if noGrav and spec['instanceType'][2]=='g': continue
        if noGrav and spec['instanceType'][0]=='a': continue
        if includePrev == False and spec['currentGeneration'] == "No": continue 
        if spec['clockSpeed'] =='unknown' and ghz !=0 : continue
        if spec['clockSpeed'] !='unknown': 
            if ghz > specGHz: continue
        if cpu > specCPU: continue
        if memory > specMem: continue
        if ec2Type[model] == 'N/A' or ec2Type[model] == '': continue
        #Check Disk
        specIop=0
        specMBps=0;
        if 'MaximumIops' in spec and spec['MaximumIops'] != '': specIop = float(spec['MaximumIops'])
        if specIop < reqDiskIOPs : continue;
        if 'MaximumThroughputInMBps' in spec and spec['MaximumThroughputInMBps'] != '': specMBps = float(spec['MaximumThroughputInMBps'] )
        if specMBps < reqDiskThroughput : continue;

        #Find Right Instance
        if float(ec2Type[model]) < minCost:
            minCost = float(ec2Type[model])
            input['Instance Type'] = ec2Type["API Name"]
            input['OS'] = os
            input['Pricing Model'] = priceModel
            input['vCPUs'] = int(specCPU)
            input['Mem GB'] = float(specMem)
            input['EC2 Hourly'] = minCost
            input['EC2 Monthly'] = minCost * 730
            #print(ec2Type["API Name"])
        
    #Find Right Disk
    input['EBS GB'] = reqDiskGB
    if reqDiskGB <= 16000 and reqDiskIOPs <= 16000 and reqDiskThroughput <= 1000:
        input['EBS Type'] = 'GP3'
        diffIOPs = reqDiskIOPs - 3000;
        diffMBps = reqDiskThroughput - 125;
        if diffIOPs < 0 : diffIOPs = 0;
        if diffMBps < 0 : diffMBps = 0;
        input['EBS Monthly'] = reqDiskGB*0.08 + diffIOPs*0.006 + diffMBps*0.048
    else: 
        input['EBS Type'] = 'IO2'
        input['EBS Monthly'] = reqDiskGB*0.138 + reqDiskIOPs*0.072
    #Calculate Backup size with 1%Daily change
    bkkSize = reqDiskGB * (1 + 0.01 * reqBUDay)
    input['BU GB'] = bkkSize
    input['BU Monthly'] = bkkSize * 0.05
    input['Total Monthly'] = input['EC2 Monthly'] + input['EBS Monthly'] + input['BU Monthly']

    return input
 

def main(argv):
    #print(argv)
    #Load File
    options = argv[1:]
    ec2Cost = ImportDictFromCSV('ec2-cost.csv')
    ec2Spec = ImportDictFromCSV('ec2-spec.csv')
    #ERROR if cannot open file
    isStop = False
    if ec2Cost == "ERROR": print('ec2-cost.csv Cannot be found. Please run UpdateEC2Price.py'); isStop = True;
    if ec2Spec == "ERROR": print('ec2-spec.csv Cannot be found. Please run UpdateEC2Price.py'); isStop = True;

    #Get requirement filename and Open 
    fileName = argv[0].split('.')
    print("Getting fron file : " + fileName[0])
    inputList = ImportDictFromCSV(argv[0])
    if inputList == "ERROR": print('ec2-spec.csv Cannot be found. Please run UpdateEC2Price.py'); isStop = True;
    if isStop: return;

    #Get EC2 instance for all VMs
    resultList = {}
    index=0;
    allTotalColumn = ['vCPUs','Mem GB','EC2 Hourly','EC2 Monthly','Req Core','Req Mem GB','Req Disk GB','Req IOPs','Req MBps', 'EBS Monthly','BU Monthly','Total Monthly','EBS GB','BU GB']
    sumAll = {}
    sumAll['Source Name'] = "Total"
    
    for input in inputList:
        result = GetLowestInstancePrice(input, ec2Cost, ec2Spec, options)
        #print(result)
        resultList[index] = result
        index += 1
        for col in allTotalColumn:
            if col in sumAll: sumAll[col] += float(result[col])
            else: sumAll[col] = float(result[col])
    
    #Prepare to write file
    now = datetime.now()
    date = str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(now.hour)+'-'+str(now.minute)+'-'+str(now.second)
    outFileName = fileName[0]+'-result-'+date+'.csv'

    #Write File
    
    print("Writing file to : " + outFileName)
    
    resultList[len(resultList)] = sumAll

    resultListStr = json.dumps(resultList, indent=2)
    with open("temp-result.json", "w") as outfile:
        outfile.write(resultListStr)

    resultObject = pd.read_json("temp-result.json", orient='index')
    resultObject.to_csv(outFileName, index=False)
    print(resultObject)
    os.remove("temp-result.json") 

if __name__ == "__main__":
   main(sys.argv[1:])

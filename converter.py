import csv
import re
import re
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
    priceModel = 'on-demand'
    os = "Linux"
    if input['Req Core']    != "": cpu = int(input['Req Core'])
    if input['Req GHz']     != "": ghz = float(input['Req GHz'])
    if input['Req Mem GB']  != "": memory = float(input['Req Mem GB'])
    if input['Req OS']  != "": os = input['Req OS']
    if input['price-model'] != '': priceModel = input['price-model'] 

    print(input["Source Name"] + " : " + str(cpu) + " cores, " + str(ghz) + " GHz, " + str(memory) + " GB mem, " + os + " OS")
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
        if noGrav and spec['instanceType'][2]=='g': continue
        if noGrav and spec['instanceType'][0]=='a': continue
        if includePrev == False and spec['currentGeneration'] == "No": continue 
        if spec['clockSpeed'] =='unknown' and ghz !=0 : continue
        if spec['clockSpeed'] !='unknown': 
            if ghz > specGHz: continue
        if cpu > specCPU: continue
        if memory > specMem: continue
        if ec2Type[model] == 'N/A' or ec2Type[model] == '': continue
        if float(ec2Type[model]) < minCost:
            minCost = float(ec2Type[model])
            input['Instance Type'] = ec2Type["API Name"]
            input['OS'] = os
            input['Pricing Model'] = priceModel
            input['vCPUs'] = int(specCPU)
            input['Memory GB'] = float(specMem)
            input['Hourly Pricing'] = minCost
            input['Monthly Pricing'] = minCost * 730
            #print(ec2Type["API Name"])
    
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
    sumReqCore = 0;
    sumReqMem = 0;
    sumCPU = 0;
    sumMem =0;
    sumHourly = 0

    for input in inputList:
        result = GetLowestInstancePrice(input, ec2Cost, ec2Spec, options)
        #print(result)
        resultList[index] = result
        index += 1
        sumCPU = sumCPU + result['vCPUs']
        sumMem = sumMem + result['Memory GB']
        sumHourly = sumHourly + result['Hourly Pricing']
        sumReqCore = sumReqCore + float(result['Req Core'])
        sumReqMem = sumReqMem + float(result["Req Mem GB"])
    
    #Prepare to write file
    now = datetime.now()
    date = str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(now.hour)+'-'+str(now.minute)+'-'+str(now.second)
    outFileName = fileName[0]+'-result-'+date+'.csv'

    #Write File
    
    print("Writing file to : " + outFileName)
    #for result in resultList:
    #    print(result["Source Name"] + " : Type : " + result["Instance Type"] + " " + str(result['vCPUs']) + " cores, " + str(result['Memory GB']) + " GB mem, " + str(result['Hourly Pricing']) + " $/hrs" + str(result['Hourly Pricing']*730) + " $/Month")
        
    sumRow = {}
    sumRow['Source Name'] = "Total"
    sumRow['Req Core'] = sumReqCore
    sumRow['Req Mem GB'] = sumReqMem
    sumRow['vCPUs'] = sumCPU
    sumRow['Memory GB'] = sumMem
    sumRow['Hourly Pricing'] = sumHourly
    sumRow['Monthly Pricing'] = sumHourly * 730;
    resultList[len(resultList)] = sumRow

    resultListStr = json.dumps(resultList, indent=2)
    with open("temp-result.json", "w") as outfile:
        outfile.write(resultListStr)

    resultObject = pd.read_json("temp-result.json", orient='index')
    resultObject.to_csv(outFileName, index=False)
    print(resultObject)
    os.remove("temp-result.json") 

if __name__ == "__main__":
   main(sys.argv[1:])

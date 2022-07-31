import csv
import re
import sys
import math
from datetime import datetime

def ImportDictFromCSV(filename):
    with open(filename, 'r',encoding='utf-8-sig') as read_obj:
        # pass the file object to DictReader() to get the DictReader object
        dict_reader = csv.DictReader(read_obj)
        # get a list of dictionaries from dct_reader
        list_of_dict = list(dict_reader)
        # print list of dict i.e. rows
        return list_of_dict

def GetInstanceTypeSpecObj(ec2Type, ec2Spec):
    for item in ec2Spec:
        if item['API Name'] == ec2Type:
            return item
    
def GetLowestInstancePrice(input, ec2Cost, ec2Spec):
    minCost = 999999.9
    cpu = 0
    ghz = 0
    memory = 0
    priceModel = 'on-demand'
    os = "Linux"
    if input['core']    != "": cpu = int(input['core'])
    if input['ghz']     != "": ghz = float(input['ghz'])
    if input['memory']  != "": memory = float(input['memory'])
    if input['os']  != "": os = input['os']
    if input['price-model'] != '': priceModel = input['price-model'] 

    print(input["Source Name"] + " : " + str(cpu) + " cores, " + str(ghz) + " GHz, " + str(memory) + " GB mem, " + os + " OS")

    for ec2Type in ec2Cost:
        #print(ec2Type)
        spec = GetInstanceTypeSpecObj(ec2Type["API Name"], ec2Spec)
        #Logic is here
        model = os + "-" + priceModel
        if spec['Clock Speed(GHz)'] =='unknown' and ghz !=0 : continue
        if spec['Clock Speed(GHz)'] !='unknown': 
            if ghz > float(spec['Clock Speed(GHz)']): continue
        if cpu > int(spec['vCPUs']): continue
        if memory > float(spec['Memory']): continue
        if ec2Type[model] == 'unavailable': continue
        if float(ec2Type[model]) < minCost:
            minCost = float(ec2Type[model])
            input['Instance Type'] = ec2Type["API Name"]
            input['OS'] = os
            input['Pricing Model'] = priceModel
            input['vCPUs'] = int(spec['vCPUs'])
            input['Memory'] = float(spec['Memory'])
            input['Hourly Pricing'] = minCost
            input['Monthly Pricing'] = minCost * 730
            #print(ec2Type["API Name"])
    
    return input
 

def main(argv):
    #print(argv)
    #Load File
    ec2Cost = ImportDictFromCSV('ec2-cost.csv')
    ec2Spec = ImportDictFromCSV('ec2-spec.csv')
    inputList = ImportDictFromCSV(argv[0])
    #Get filename 
    fileName = argv[0].split('.')
    print("Getting fron file : " + fileName[0])
    #Get EC2 instance for all VMs
    resultList = []
    for input in inputList:
        result = GetLowestInstancePrice(input, ec2Cost, ec2Spec)
        #print(result)
        resultList.append(result)
    
    #Prepare to write file
    now = datetime.now()
    date = str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(now.hour)+'-'+str(now.minute)+'-'+str(now.second)
    outFileName = fileName[0]+'-result-'+date+'.csv'

    #Write File
    sumCPU = 0;
    sumMem =0;
    sumHourly = 0
    print("Writing file to : " + outFileName)
    for result in resultList:
        print(result["Source Name"] + " : Type : " + result["Instance Type"] + " " + str(result['vCPUs']) + " cores, " + str(result['Memory']) + " GB mem, " + str(result['Hourly Pricing']) + " $/hrs" + str(result['Hourly Pricing']*730) + " $/Month")
        sumCPU = sumCPU + result['vCPUs']
        sumMem = sumMem + result['Memory']
        sumHourly = sumHourly + result['Hourly Pricing']
    sumRow = {}
    sumRow['Source Name'] = "Total"
    sumRow['vCPUs'] = sumCPU
    sumRow['Memory'] = sumMem
    sumRow['Hourly Pricing'] = sumHourly
    sumRow['Monthly Pricing'] = sumHourly * 730;

    with open(outFileName, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(resultList[0].keys())
        for result in resultList:
            writer.writerow(result[index] for index in result.keys())
        writer.writerow(sumRow[index] for index in sumRow.keys())

if __name__ == "__main__":
   main(sys.argv[1:])
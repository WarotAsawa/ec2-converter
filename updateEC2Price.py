from turtle import back
from unittest import result
import boto3
import json, csv
import os
import pandas as pd
from pkg_resources import resource_filename
from datetime import datetime

# Set FIlter tp Singapore Only
FLT = '[{{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"}},'\
      '{{"Field": "location", "Value": "{r}", "Type": "TERM_MATCH"}},'\
      '{{"Field": "capacitystatus", "Value": "Used", "Type": "TERM_MATCH"}}]'

def translate_platform_name(operating_system, preinstalled_software):
    os = {
        "Linux": "Linux",
        "RHEL": "RHEL",
        "Red Hat Enterprise Linux with HA": "RHEL HA",
        "SUSE": "SLES",
        "Windows": "Windows",
        "Linux/UNIX": "Linux",
        "Red Hat Enterprise Linux": "RHEL",
        "SUSE Linux": "SLES",
    }
    software = {
        "":"",
        "NA": "",
        "SQL Std": " SQL Std",
        "SQL Web": " SQL Web",
        "SQL Ent": " SQL Ent",
    }
    return os[operating_system] + software[preinstalled_software]

# Backup Old File
def backupOldFile():
     #Backup Old File
    now = datetime.now()
    date = str(now.year)+'-'+str(now.month)+'-'+str(now.day)+'-'+str(now.hour)+'-'+str(now.minute)+'-'+str(now.second)
    try: os.rename("ec2-spec.csv", "ec2-spec-bkk-"+date+".csv")
    except: print("ec2-spec.csv Not Found")
    try: os.rename("ec2-cost.csv", "ec2-cost-bkk-"+date+".csv")
    except: print("ec2-cost.csv Not Found")

# Get more EC2 instance type spec
def get_ec2_spec():
    results = {}
    nextToken = "INIT"
    
    while nextToken != "END":
        #If INIT then send without token, else sent with token
        if nextToken == "INIT": data = ec2Client.describe_instance_types();
        else: data = data = ec2Client.describe_instance_types(NextToken=nextToken);

        #If no more Token then END the loop
        if "NextToken" in data: nextToken = data["NextToken"]
        else: nextToken = "END"
        for i in range(0,len(data['InstanceTypes'])-1):
            currentData = data['InstanceTypes'][i]
            instanceName = currentData['InstanceType']
            #Get Needed info
            results[instanceName] = {}
            if 'Hypervisor' in currentData: results[instanceName]['Hypervisor'] = currentData['Hypervisor']
            else: results[instanceName]['Hypervisor'] = 'nitro'
            if currentData['EbsInfo']['EbsOptimizedSupport'] != 'unsupported':
                results[instanceName]['MaximumThroughputInMBps'] = currentData['EbsInfo']['EbsOptimizedInfo']['MaximumThroughputInMBps']
                results[instanceName]['MaximumIops'] = currentData['EbsInfo']['EbsOptimizedInfo']['MaximumIops']
            else:
                results[instanceName]['MaximumThroughputInMBps'] = 50
                results[instanceName]['MaximumIops'] = 100
    
    return results

# Get current AWS price for an on-demand instance
def get_price(region):
    f = FLT.format(r=region)
    hourPerMonth = 730
    #Set required spec for ec2
    specRow = ["instanceType","enhancedNetworkingSupported","intelTurboAvailable","memory","dedicatedEbsThroughput","vcpu","classicnetworkingsupport","storage","intelAvx2Available","physicalProcessor","clockSpeed","ecu","networkPerformance","vpcnetworkingsupport","tenancy","normalizationSizeFactor","intelAvxAvailable","processorFeatures","licenseModel","currentGeneration","preInstalledSw","processorArchitecture"]
    #Temp list space for output
    specMatrix = []
    priceMatrix = {}
    nextToken = "INIT"
    totalPage = 0;
    totalPrice = 0;
    #Get Storage and Hypersisor spec
    moreSpec = get_ec2_spec()
    while nextToken != "END":
        #If INIT then send without token, else sent with token
        if nextToken == "INIT": data = priceClient.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f));
        else: data = priceClient.get_products(ServiceCode='AmazonEC2', Filters=json.loads(f),NextToken=nextToken);

        #If no more Token then END the loop
        if "NextToken" in data: nextToken = data["NextToken"]
        else: nextToken = "END"
        totalPage += 1;
        totalPrice += len(data['PriceList']);
        print("Page: " + str(totalPage) + " with " + str(len(data['PriceList'])) + " records")
        #Get all returned PriceList
        for i in range(0,len(data['PriceList'])-1):
            currentData = json.loads(data['PriceList'][i])
            productAttributes = currentData["product"]["attributes"]
            instanceType = productAttributes["instanceType"]
            #Update Instance Spec if found new instance
            if (instanceType in priceMatrix) == False:
                priceMatrix[instanceType] = {}
                priceMatrix[instanceType]["API Name"] = instanceType
                newInstanceSpec = []
                for attr in specRow:
                    if attr in productAttributes:
                        newInstanceSpec.append(productAttributes[attr])
                    else: newInstanceSpec.append('')
                #Add more spec
                for attr in moreSpec['m1.medium']:
                    if instanceType in moreSpec: newInstanceSpec.append(moreSpec[instanceType][attr])
                    else: newInstanceSpec.append('')
                specMatrix.append(newInstanceSpec)
            
            #Add on-demand and all 12 RI Pricing
            osName = productAttributes['operatingSystem']
            sw = productAttributes["preInstalledSw"]
            ossw = translate_platform_name(osName,sw)
            #Get on Demand Price
            od = currentData['terms']['OnDemand']
            id1 = list(od)[0]
            id2 = list(od[id1]['priceDimensions'])[0]
            hourlyPrice = od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']
            priceMatrix[instanceType][ossw+"-on-demand"] = float(hourlyPrice)

            #Get Reserved Pricing ! Some instance has no reserved offerring at all
            if 'Reserved' in currentData['terms']: rsSet = currentData['terms']['Reserved']
            else: continue;
            rsSetList = list(rsSet)
            for rs in rsSetList:
            
                #Get rs type (1,3 years), convertible or not, upfront type
                rs = rsSet[rs]
                termAttributes = rs["termAttributes"]
                rsType = ""
                #Set Convertible if is "convertible" then RIC or else if is "standard" then RI
                if 'convertible' in termAttributes['OfferingClass']: rsType = rsType + "-RIC"
                else: rsType = rsType + "-RI"
                #Set Year
                year = 1
                if '3' in termAttributes['LeaseContractLength']: rsType = rsType + "-3Y"; year=3
                else: rsType = rsType + "-1Y"
                #Set Upfront type
                if 'All' in  termAttributes['PurchaseOption']: rsType = rsType + "-AUF"; 
                elif 'Partial' in termAttributes['PurchaseOption']: rsType = rsType + "-PUF"
                else: rsType = rsType + "-NUF"

                #Get Upfront and Hourly Cost
                offerList = list(rs["priceDimensions"])
                price = 0
                for offer in offerList:
                    offer = rs["priceDimensions"][offer]
                    offerPrice = offer["pricePerUnit"]["USD"]
                    #If hourly, it means hourly, other wise is upfront price
                    if offer["unit"] == "Hrs": price += float(offerPrice)
                    else: price += float(offerPrice) / year / 365 / 24

                #Set Price
                plan = ossw + rsType
                if price <= 0: priceMatrix[instanceType][plan] = "N/A"
                else: priceMatrix[instanceType][plan] = price
    print("Total Records: " + str(totalPrice))
    #Prepare to write new spec file
    #Add more spec row
    for attr in moreSpec['m1.medium']:
        specRow.append(attr)
    outFileName = 'ec2-spec.csv'
    with open(outFileName, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(specRow)
        for spec in specMatrix:
            writer.writerow(spec)
    #Write price file to json and convert to csv
    # Writing to sample.json
    priceMatrixStr = json.dumps(priceMatrix, indent=2)
    with open("temp-price.json", "w") as outfile:
        outfile.write(priceMatrixStr)
    #use pandas to convert json to csv
    pdObj = pd.read_json("temp-price.json", orient='index')
    pdObj.to_csv('ec2-cost.csv', index=False)
    
    os.remove("temp-price.json") 

    return "Finish update ec-spec.csv and ec2-cost.csv file"

# Translate region code to region name. Even though the API data contains region code
def get_region_name(region_code):
    default_region = 'US East (N. Virginia)'
    endpoint_file = resource_filename('botocore', 'data/endpoints.json')
    try:
        with open(endpoint_file, 'r') as f:
            data = json.load(f)
        return data['partitions'][0]['regions'][region_code]['description'].replace('Europe', 'EU')
    except IOError:
        return default_region


# Use AWS Pricing API and ec2 describe through Boto3 via us-east-1 pricing endpoint
priceClient = boto3.client('pricing', region_name='us-east-1')
ec2Client = boto3.client('ec2', region_name='us-east-1')

# Back up old file
backupOldFile()
# Get current price for a given instance, region and os
result = get_price(get_region_name('ap-southeast-1'))
print(result)
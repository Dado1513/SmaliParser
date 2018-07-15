import os
import re
import sys
import threading
import codecs
import time
import argparse
import subprocess

file_2_method = dict()
method_2_value = dict()
all_url = dict()

def get_methods(content):
    """
    gets all methods in a single smali file content
    :param content: smali file content
    :rtype: list of lists
    :return: [0] - method name
                [1] - method parameters
                [2] - method return value
                [3] - method data
    """
    pattern_method_data = re.compile(r'^\.method.+?\ (.+?(?=\())\((.*?)\)(.*?$)(.*?(?=\.end\ method))', re.MULTILINE | re.DOTALL)

    data = re.findall(pattern_method_data, content)
    return data

def get_called_methods(line):
    """
    gets all the method called inside a smali method data. works just fine with a single smali line
    :param content: content of the smali data to be parsed
    :rtype: list of lists
    :return: [0] - called method parameters
                [1] - called method object type
                [2] - called method name
                [3] - called method parameters object type
                [4] - called method return object type
    """
    pattern_called_methods = re.compile(r'invoke-.*?\ {(.*?)}, (.+?(?=;))\;\-\>(.+?(?=\())\((.*?)\)(.*?)(?=$|;)', re.MULTILINE | re.DOTALL)
    data = re.findall(pattern_called_methods, line)
    return data

def get_line(method_data):
    """
        from method of class get const value
    """
    patter_line = re.compile("[.line|.local*](.*?)(?=return|.line)", re.MULTILINE | re.DOTALL)
    data = re.findall(patter_line,method_data)
    return data

def from_const_get_value(line,all_const):
    """
        from line and all const inside (v0,v1) ecc
        get value of this if assigned at const
    """
    const = all_const.split(",")
    name_to_value = dict()
    for c in const:
        c = c.replace(" ","")
        pattern_const = re.compile("const.* {0}, (.*)".format(c))
        data = re.findall(pattern_const,line)
        
        name_to_value[c] = data[-1] if len(data) > 0 else None
    return name_to_value
    #print(name_to_value)


def find_url_inside(directory_to_search):
    """
        get list of all url inside smali file
    """    
    url_re = "https?:\/\/[a-zA-Z0-9@:%._\+~#=/][^\s|^\"|^)]+"
    list_url = subprocess.check_output(["egrep","-r","-oh",url_re,directory_to_search]).decode('utf-8').strip()
    list_url =  list_url.split()
    list_url = list(set(list_url))
    list_url = [x for x in list_url if x.startswith("http") or x.startswith("https")]
    all_url["url"] = list_url

def search_method(list_file,lock,list_method):
    for file in list_file:
        
        if file.endswith(".smali"):
            file_read = str(open(file,"r").read())
            methods = get_methods(file_read)
            for method in methods:
                lines = get_line(method[3])
                for line in lines:
                    # print (line)
                    method_called = get_called_methods(line) # tutti i metodi nella linea
                    for m in method_called:
                        if m[2] in list_method:
                            # print(m[2])
                            value = from_const_get_value(line,m[0]) # get value passed to method
                            
                            if file not in file_2_method.keys():
                                file_2_method[file] = list()
                                file_2_method[file].append(m[2]) # get method used in this file
                            else:
                                file_2_method[file] = list(set().union(file_2_method[file],[m[2]]))
                            
                            # lock.acquire()
                            if m[2] not in method_2_value.keys() :
                                method_2_value[m[2]] = list()
                                method_2_value[m[2]].append(value)
                            else:
                                method_2_value[m[2]].append(value)
                                
                            # lock.release()
                            # print()
        # try:
        #     #file_read = str(open(file,"r").read())
        #     if not file.endswith(".html"):
        #         file_read = codecs.open(file,"r",encoding="utf-8",errors='ignore').read()
        #         find_url_inside(file, file_read)
        # except Exception as e:
        #     print("Exception file e {0}: {1} ".format(e,file))


def start(dir, list_method):
    
    """
        Smali Parser that be able to parsing smali code
        and to get when method "method" has been used and the 
        how parameter has been passed inside or if that method has been called
    """
    time_start = time.time()
    threadLock = threading.Lock()
    list_file = list()
    dir_apk = dir
    use_grep = True
    if use_grep:
        for m in list_method:
            output = subprocess.check_output(["grep","-rl",m,dir_apk]).decode('utf-8').strip()
            list_file = list(set().union(list_file,output.split("\n")))
         
    else:
        for root, dirs, files in os.walk(dir_apk):
            for file in files:
                list_file.append(os.path.join(root, file)) # append all file in list 
        # list_method = ["loadUrl","addJavascriptInterface","evaluateJavaScript"]
    threads = []
    # print(len(list_file))
    numero_thread_max = int(len(list_file) / 50) # ogni thread analizza 50 file
    print("thread creati: {0}".format(numero_thread_max))
    for i in range(0,numero_thread_max):
        if i < numero_thread_max -1:
            thread = threading.Thread(target=search_method,args=(list_file[i*numero_thread_max:(i+1)*numero_thread_max-1],threadLock,list_method,))
        else:
            thread = threading.Thread(target=search_method,args=(list_file[i*numero_thread_max:],threadLock,list_method,))
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join()
    
    # print(file_2_method) # per ogni file i metodi all'interno
    print(method_2_value) # per ogni metodo un dizionario che comprende tutti i valori passati come parametri
    for keys in method_2_value.keys(): # per ogni metodo
        values = method_2_value[keys] # prendo tutta la lista dei vari parametri
        print("Method: {0}".format(keys))
        for value in values: # per ogni dizionario di parametri
            print(list(value.values()))

    find_url_inside(dir_apk) # tutte le url all'interno dell'apk (fare un thread separato)
    print(all_url["url"]) # tutte le url all'interno dell'apk
    time_end = time.time() 
    print("Exec in {0}".format(time_end - time_start))
    # for file in files:
        # if file.endswith(".smali") :

def main():
    parser = argparse.ArgumentParser(description="Smali Parser that search if method was used and with how parameter",
                    usage="\n\ntpython smaliparser.py -l loadUrl evaluateJavaScript -d dircreatedapktool",
                    epilog="Author: Davide Caputo")
    parser.add_argument('-m','--methods', nargs='+', help='<Required> Set flag', required=True)
    parser.add_argument('-d','--dir',help=" Dir to analyze",required=True)
    args = parser.parse_args()

    start(args.dir, args.methods)
    

if __name__ == "__main__":
    main()

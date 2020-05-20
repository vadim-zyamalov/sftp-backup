import argparse
import os, os.path
import sys
import datetime
import rarfile
import pysftp

parser = argparse.ArgumentParser(add_help=True)
parser.add_argument('-s', '--source',
                    nargs='?',
                    type=str,
                    default='',
                    help='Remote path',
                    dest='source',
                    required=True)
parser.add_argument('-t', '--target',
                    nargs='?',
                    type=str,
                    default='',
                    help='Local path',
                    dest='target',
                    required=True)
args = parser.parse_args()


def read_credentials(filename):
    result = {}
    with open(filename, 'r') as cred:
        for line in cred:
            tmp = line.split(':')
            result[tmp[0].strip()] = tmp[1].strip()
    return result


def norm_path(txt):
    return txt.replace(os.sep, '/')


def os_path(txt):
    return txt.replace('/', os.sep)


def sftp_folder_process(handler, startpath, path, exclude=[]):
    print(startpath + path)
    if (startpath + path) in exclude:
        return {}
    filelist = handler.listdir(startpath + path)
    result = {}
    for item in filelist:
        if handler.isfile(startpath + path + item):
            if os.path.splitext(item)[1] in excludeext:
                continue
            if item.startswith('~$'):
                continue
            attr = handler.stat(startpath + path + item)
            result[path + item] = int(attr.st_mtime)
        else:
            result.update(sftp_folder_process(handler, startpath, path + item + '/', exclude))
    return result


def folder_process(startpath, path, exclude=[]):
    print(startpath + path)
    if (startpath + path) in exclude:
        return {}
    filelist = os.listdir(startpath + path)
    result = {}
    for item in filelist:
        if os.path.splitext(item)[1] in excludeext:
            continue
        if item.startswith('~$'):
            continue
        if os.path.isfile(startpath + path + item):
            attr = os.stat(startpath + path + item)
            result[norm_path(path + item)] = int(attr.st_mtime)
            if os.path.splitext(item)[1] == '.rar':
                result.update(rar_process(startpath, path, item))
        else:
            result.update(folder_process(startpath, path + item + os.path.sep, exclude))
    return result


def rar_process(startpath, path, item):
    result = {}
    with rarfile.RarFile(startpath + path + item) as rar:
        rarlist = rar.infolist()
        if len(rarlist) > 1:
            return result
        else:
            if os.path.splitext(item)[0] == rarlist[0].filename:
                tmp_time = rarlist[0].mtime if rarlist[0].mtime is not None else datetime.datetime(*rarlist[0].date_time)
                result[norm_path(path + rarlist[0].filename)] = datetime.datetime.timestamp(tmp_time)
    return result


def sftp_process(fin, all):
    print('{:10} of {:10} ({:8.3%})'.format(fin, all, fin/all), end='\r')


if __name__ == '__main__':
    credentials = read_credentials('credentials.txt')
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    ## startingsource = '/E:/zyamalov/_YANDEX_/_YANDEX_CODE_/'
    startingsource = args.source
    ## startingtarget = 'E:\\Zyamalov\\_YANDEX_\\_YANDEX_CODE_\\'
    startingtarget = args.target
    path = ''

    excludedir = []
    with open('excludedir.txt', 'r') as file:
        for line in file:
            excludedir.append(line.strip())

    excludeext = []
    with open('excludeext.txt', 'r') as file:
        for line in file:
            excludeext.append(line.strip())

    check_archives = []
    with open('check_archives.txt', 'r') as file:
        for line in file:
            check_archives.append(line.strip())

    ## TARGET
    targetlist = folder_process(startingtarget, path)

    with open('filelistt', 'w', encoding='utf-8') as file:
        for item in targetlist:
            file.write(item + '\n')

    ## SOURCE
    with pysftp.Connection(credentials['hostname'], 
                           username = credentials['username'], 
                           password = credentials['password'], 
                           cnopts = cnopts) as sftp:
        sourcelist = sftp_folder_process(sftp, startingsource, path, excludedir)
    sftp.close()

    with open('filelists', 'w', encoding='utf-8') as file:
        for item in sourcelist:
            file.write(item + '\n')

    ## RESULTLIST
    resultlist = []
    for item in sourcelist:
        if not item in targetlist:
            if os.path.splitext(item)[1] in check_archives:
                tmp_name = os.path.splitext(item)[0] + '.rar'
                if not tmp_name in targetlist:
                    resultlist.append((item, os_path(item)))
                if (tmp_name in targetlist) and (sourcelist[item] > targetlist[tmp_name]):
                    resultlist.append((item, os_path(item)))
            else:
                resultlist.append((item, os_path(item)))
        else:
            if (sourcelist[item] > targetlist[item]):
                resultlist.append((item, os_path(item)))

    with open('filelist', 'w', encoding='utf-8') as file:
        for item in resultlist:
            file.write('{}\t{}\n'.format(item[0], item[1]))
    
    with pysftp.Connection(credentials['hostname'], 
                           username = credentials['username'], 
                           password = credentials['password'], 
                           cnopts = cnopts) as sftp:
        index = 0
        for fromfile, tofile in resultlist:
            index += 1
            print(' '*50, end='\r')
            print('[{}:{}] Getting {}'.format(index, len(resultlist), tofile))
            targetpath = os.path.dirname(startingtarget + tofile)
            if not os.path.exists(targetpath):
                os.makedirs(targetpath)
            sftp.get(startingsource + fromfile, localpath=startingtarget + tofile, callback=sftp_process, preserve_mtime=True)
    sftp.close()
    
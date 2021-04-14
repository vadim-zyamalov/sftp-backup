import os
import os.path
import json
import datetime
import rarfile
import pysftp
import shlex
import subprocess


def read_settings(filename):
    with open(filename, 'r', encoding='utf-8') as sfile:
        result = json.load(sfile)
    return result


def norm_path(txt):
    return txt.replace(os.sep, '/')


def os_path(txt):
    return txt.replace('/', os.sep)


def sftp_folder_process(handler, startpath, path, excludedir=[], excludeext=[]):
    print(startpath + path)
    if (startpath + path) in excludedir:
        return {}
    try:
        filelist = handler.listdir(startpath + path)
    except FileNotFoundError:
        return {}
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
            result.update(sftp_folder_process(handler, startpath, path + item + '/', excludedir, excludeext))
    return result


def folder_process(startpath, path, exclude=[]):
    print(startpath + path)
    if (startpath + path) in exclude:
        return {}
    try:
        filelist = os.listdir(startpath + path)
    except FileNotFoundError:
        return {}
    result = {}
    for item in filelist:
        if os.path.splitext(item)[1] in exclude:
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
    try:
        with rarfile.RarFile(startpath + path + item) as rar:
            rarlist = rar.infolist()
            if len(rarlist) > 1:
                return result
            else:
                if os.path.splitext(item)[0] == rarlist[0].filename:
                    tmp_time = rarlist[0].mtime if rarlist[0].mtime is not None else datetime.datetime(*rarlist[0].date_time)
                    result[norm_path(path + rarlist[0].filename)] = datetime.datetime.timestamp(tmp_time)
    except rarfile.NeedFirstVolume:
        pass
    return result


def sftp_process(fin, all):
    print('{:10} of {:10} ({:8.3%})'.format(fin, all, fin/all), end='\r')


if __name__ == '__main__':
    settings = read_settings('settings.json')
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    for pair in settings['sync']:
        ## TARGET
        targetlist = {}
        targetlist = folder_process(pair['target'], '', settings['exclude'])

        ## SOURCE
        for tmpsource in pair['source']:
            sourcelist = {}
            with pysftp.Connection(settings['sftp']['hostname'], 
                                   username = settings['sftp']['username'],
                                   password = settings['sftp']['password'], 
                                   cnopts = cnopts) as sftp:
                sourcelist = sftp_folder_process(sftp, tmpsource, '', pair['exclude'], settings['exclude'])
            sftp.close()

            ## RESULTLIST
            resultlist = []
            for item in sourcelist:
                if not item in targetlist:
                    if os.path.splitext(item)[1] in settings['archives']:
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

            with pysftp.Connection(settings['sftp']['hostname'], 
                                   username = settings['sftp']['username'],
                                   password = settings['sftp']['password'], 
                                   cnopts = cnopts) as sftp:
                index = 0
                for fromfile, tofile in resultlist:
                    index += 1
                    print(' '*50, end='\r')
                    print('[{}:{}] Getting {}'.format(index, len(resultlist), tofile))
                    targetpath = os.path.dirname(pair['target'] + tofile)
                    if not os.path.exists(targetpath):
                        os.makedirs(targetpath)
                    sftp.get(tmpsource + fromfile, localpath=pair['target'] + tofile, callback=sftp_process, preserve_mtime=True)
            sftp.close()

        command = '{}'.format(os.getcwd()) + os.sep + 'backup.bat "{}"'.format(pair['target'])
        with subprocess.Popen(command, cwd=os.getcwd(), shell=False, stdout=subprocess.PIPE) as proc:
            try:
                outs, errs = proc.communicate()
            except TimeoutExpired:
                proc.kill()
                outs, errs = proc.communicate()
            proc.kill()
import os
import os.path
import json
import datetime
import rarfile
import pysftp
import subprocess
import sys


def read_settings(filename):
    with open(filename, 'r', encoding='utf-8') as sfile:
        result = json.load(sfile)
    return result


def norm_path(txt):
    return txt.replace(os.sep, '/')


def os_path(txt):
    return txt.replace('/', os.sep)


def sftp_folder_process(handler,
                        startpath,
                        path,
                        excludedir=[],
                        excludeext=[]):
    print(startpath + path)
    if startpath + path in excludedir:
        return {}
    try:
        filelist = handler.listdir(startpath + path)
    except FileNotFoundError:
        return {}
    result = {}
    for loop_file in filelist:
        if handler.isfile(startpath + path + loop_file):
            if os.path.splitext(loop_file)[1] in excludeext:
                continue
            if loop_file.startswith('~$'):
                continue
            attr = handler.stat(startpath + path + loop_file)
            result[path + loop_file] = int(attr.st_mtime)
        else:
            result.update(sftp_folder_process(handler,
                                              startpath,
                                              path + loop_file + '/',
                                              excludedir,
                                              excludeext))
    return result


def folder_process(startpath,
                   path,
                   exclude=[]):
    print(startpath + path)
    if startpath + path in exclude:
        return {}
    try:
        filelist = os.listdir(startpath + path)
    except FileNotFoundError:
        return {}
    result = {}
    for loop_file in filelist:
        if os.path.splitext(loop_file)[1] in exclude:
            continue
        if loop_file.startswith('~$'):
            continue
        if os.path.isfile(startpath + path + loop_file):
            attr = os.stat(startpath + path + loop_file)
            result[norm_path(path + loop_file)] = int(attr.st_mtime)
            if os.path.splitext(loop_file)[1] == '.rar':
                result.update(rar_process(startpath, path, loop_file))
        else:
            result.update(folder_process(startpath,
                                         path + loop_file + os.path.sep,
                                         exclude))
    return result


def rar_process(startpath, path, rar_file):
    result = {}
    try:
        with rarfile.RarFile(startpath + path + rar_file) as rar:
            rarlist = rar.infolist()
            if len(rarlist) > 1:
                return result
            if os.path.splitext(rar_file)[0] == rarlist[0].filename:
                tmp_time = rarlist[0].mtime \
                    if rarlist[0].mtime is not None \
                    else datetime.datetime(*rarlist[0].date_time)
                result[norm_path(path + rarlist[0].filename)] = \
                    datetime.datetime.timestamp(tmp_time)
    except rarfile.NeedFirstVolume:
        pass
    return result


def sftp_process(fin, total):
    print(f"{fin:10} of {total:10} ({fin/total:8.2%})", end='\r')


if __name__ == '__main__':
    settings = read_settings('settings.json')
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None

    for pair in settings['sync']:
        # TARGET
        targetlist = {}
        targetlist = folder_process(pair['target'], '', settings['exclude'])

        # SOURCE
        for tmpsource in pair['source']:
            sourcelist = {}
            with pysftp.Connection(settings['sftp']['hostname'],
                                   username=settings['sftp']['username'],
                                   password=settings['sftp']['password'],
                                   cnopts=cnopts) as sftp:
                sourcelist = sftp_folder_process(sftp,
                                                 tmpsource,
                                                 '',
                                                 pair['exclude'],
                                                 settings['exclude'])
            sftp.close()

            # RESULTLIST
            resultlist = []
            for elem in sourcelist:
                if elem not in targetlist:
                    if os.path.splitext(elem)[1] in settings['archives']:
                        tmp_name = os.path.splitext(elem)[0] + '.rar'
                        if tmp_name not in targetlist:
                            resultlist.append((elem, os_path(elem)))
                        if (tmp_name in targetlist) and \
                           (sourcelist[elem] > targetlist[tmp_name]):
                            resultlist.append((elem, os_path(elem)))
                    else:
                        resultlist.append((elem, os_path(elem)))
                else:
                    if sourcelist[elem] > targetlist[elem]:
                        resultlist.append((elem, os_path(elem)))

            with pysftp.Connection(settings['sftp']['hostname'],
                                   username=settings['sftp']['username'],
                                   password=settings['sftp']['password'],
                                   cnopts=cnopts) as sftp:
                index = 0
                for fromfile, tofile in resultlist:
                    index += 1
                    print(' '*50, end='\r')
                    print(f"[{index}:{len(resultlist)}] Getting {tofile}")
                    targetpath = os.path.dirname(pair['target'] + tofile)
                    if not os.path.exists(targetpath):
                        os.makedirs(targetpath)
                    sftp.get(tmpsource + fromfile,
                             localpath=pair['target'] + tofile,
                             callback=sftp_process,
                             preserve_mtime=True)
            sftp.close()

        command = '{}'.format(os.getcwd()) + \
            os.sep + \
            'backup.bat "{}"'.format(pair['target'])
        subprocess.run(command,
                       cwd=os.getcwd(),
                       shell=False,
                       stdout=sys.stdout)

#!/usr/bin/env python
# -*- encoding:utf-8 -*-

import os
import sys
import glob
import subprocess
import getopt

#config
g_input = 'COMAKE'
g_output = 'Makefile'
g_enable_update_deps = False

g_cur_dir = os.getcwd()
g_basedir = os.path.dirname(g_cur_dir) 
g_cxx = 'g++'
g_cxx_flags = ''
g_ld_flags = ''
g_include_path = ['.', './include/']
g_include_str = ''
g_dep_libs = [] 
g_apps = {}
g_libs = {}
g_deps = []
g_protoc = ''
g_thrift = ''
g_cpps = set()
g_protos = set()
g_thrifts = set()
g_content = ''
g_output_dir = './output'

def log_warning(str):
    print("\033[31m WARNING: " + str + "\033[0m" )

def log_notice(str):
    print("\033[32m NOTICE: " + str + "\033[0m" )


def CXX(str):
    global g_cxx
    g_cxx = str

def CXXFLAGS(str):
    global g_cxx_flags
    g_cxx_flags = str

def LDFLAGS(str):
    global g_ld_flags
    g_ld_flags = str

def PROTOC(str):
    global g_protoc
    g_protoc = str

def THRIFT(str):
    global g_thrift
    g_thrift = str

def INCLUDE(path_arr):
    global g_include_path
    g_include_path = g_include_path + path_arr 

def DEP_LIB(lib_arr):
    global g_dep_libs
    g_dep_libs = g_dep_libs + lib_arr

def OUTPUT(str):
    global g_output_dir
    g_output_dir = str

def GLOB(str):
    files = []
    for block in str.split(' '):
        files.extend(glob.glob(block))
    return [os.path.abspath(x) for x in list(set(files))]

def _execute(command):
    p = subprocess.Popen(command,
                        shell=True,
                        bufsize=0,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
    (out, err) = p.communicate()
    return (p.returncode, err, out)

def _generate_pb_files(proto):
    global g_protoc
    proto_dir = os.path.dirname(proto)
    (ret, err, out) = _execute('%s -I=%s --cpp_out=%s %s' % (g_protoc, proto_dir, proto_dir, proto))
    if 0 != ret:
        log_warning('protoc error, proto[%s] msg[%s]' % (proto, err))
        sys.exit(1)
    return [proto[0 : proto.rfind('.')] + '.pb.cc']

def _generate_thrift_files(thrift):
    global g_thrift
    thrift_dir = os.path.dirname(thrift)
    result_list = []
    before_set = set()
    after_set = set()
    (ret, err, out) = _execute('ls %s --full-time -1' % (thrift_dir))
    if 0 != ret:
        log_warning('ls error, [%s]' % (err))
        sys.exit(1)
    for line in out.split('\n'):
        fields = line.split()
        if len(fields) >= 9: 
            before_set.add(fields[6] + ' ' + fields[8])
    (ret, err, out) = _execute('%s -out %s --gen cpp %s' % (g_thrift, thrift_dir, thrift))
    if 0 != ret:
        log_warning('thrift error, thrift[%s] msg[%s]' % (thrift, err))
        sys.exit(1)
    (ret, err, out) = _execute('ls %s --full-time -1' % (thrift_dir))
    if 0 != ret:
        log_warning('ls error, [%s]' % (err))
        sys.exit(1)
    for line in out.split('\n'):
        fields = line.split()
        if len(fields) >= 9: 
            after_set.add(fields[6] + ' ' + fields[8])
    for file in after_set - before_set:
        if file.endswith('_server.skeleton.cpp'):
            os.system('rm %s/%s' % (thrift_dir, file.split()[1]))
            continue
        elif file.endswith('.cpp'):
            result_list.append(file)
    return [thrift_dir + '/' + x.split()[1] for x in result_list]

def DEP(module, version):
    global g_deps
    g_deps.append((module, version))
    pass

def APP(bin_name, target_files):
    global g_apps 
    global g_cpps
    global g_protos
    global g_thrifts
    targets = []
    for target in target_files:
        if target.endswith('.proto'):
            g_protos.add(target)
            targets.append(target)
        elif target.endswith('.thrift'):
            g_thrifts.add(target)
            targets.append(target)
        else:
            g_cpps.add(target)
            targets.append(target)
    g_apps[bin_name] = targets

def STATIC_LIB(lib_name, cpp_files, header_files):
    global g_libs
    global g_cpps
    targets = []
    for cpp in cpp_files:
        g_cpps.add(cpp)
        targets.append(cpp)
    g_libs[_get_lib_file(lib_name)] = (targets, header_files)

def _add_content(str):
    global g_content 
    g_content += str

def _add_content_ext(name, is_phony, depend_list, action_list):
    if is_phony is True: 
        _add_content('.PHONY:%s\n' % (name))
    _add_content('%s:' % (name))
    for d in depend_list:
        _add_content('%s \\\n' % (d))
    _add_content('\n')
    for a in action_list:
        _add_content('\t%s\n' % (a))

def _get_lib_file(str):
    return 'lib' + str + '.a' 

def _get_object_file(str):
    idx = str.rfind('.')
    if -1 == idx:
        return None
    else:
        return str[0 : idx] + '.o'

def _get_single_obj_str(cpp):
    global g_include_str
    (ret, err, out) = _execute('g++ -std=gnu++11 -MM %s %s ' % (g_include_str, cpp))
    if 0 != ret:
        log_warning(err)
        return None
    out = os.path.dirname(cpp) + '/' + out
    out += '\t$(CXX) $(INCPATH) $(CXXFLAGS) -c -o %s %s\n' % (_get_object_file(cpp), cpp)
    return out

def _generate_env():
    global g_ld_flags
    global g_include_path
    global g_include_str
    global g_basedir
    global g_cur_dir
    global g_dep_libs 
    _add_content('#---------- env ----------\n')
    _add_content('CXX=%s\n' % (g_cxx))
    _add_content('CXXFLAGS=%s\n' % (g_cxx_flags))
    (ret, err, out) = _execute("find %s \\( -path '*/include' -o -path '*/output/include' \\) -type d | grep -v '%s/'" % (g_basedir, g_cur_dir))
    if 0 != ret:
        log_warning('get include dirs error, base_dir[%s] err[%s]' % (g_basedir, err))
        sys.exit(1)
    g_include_path = g_include_path + out.split() 
    g_include_str = ' '.join(['-I' + x for x in g_include_path])
    _add_content('INCPATH=%s\n' % (g_include_str))

    (ret, err, out) = _execute("find %s \\( -path '*/lib/*.a' -o -path '*/output/lib/*.a' \\) -type f | grep -v '%s/'" % (g_basedir, g_cur_dir))
    if 0 != ret:
        log_warning('get libs error, base_dir[%s], err[%s]' % (g_basedir, err))
        #sys.exit(1)
    _add_content('LIBPATH=-Xlinker "-(" %s %s -Xlinker "-)"\n' % (g_ld_flags, ' '.join(g_dep_libs + out.split())))

    _add_content('\n\n')

def _generate_phony():
    global g_apps
    global g_libs
    global g_cpps
    global g_output_dir
    _add_content('#---------- phony ----------\n')
    target_list = ['prepare']
    target_list.extend(g_apps.keys())
    target_list.extend(g_libs.keys())
    _add_content_ext('all', True, target_list, [])
    _add_content('\n')
    prepare_cmds = []
    if 0 != len(g_apps):
        prepare_cmds.append('mkdir -p %s/bin' % g_output_dir)
    if 0 != len(g_libs):
        prepare_cmds.append('mkdir -p %s/lib %s/include' % (g_output_dir, g_output_dir))
    _add_content_ext('prepare', True, [], prepare_cmds)
    _add_content('\n')
    _add_content_ext('clean', 
                     True, 
                     [], 
                     ['rm -rf %s %s' % (' '.join([_get_object_file(x) for x in g_cpps]), g_output_dir)])
    _add_content('\n\n')

def _generate_link_part():
    global g_apps
    global g_output_dir
    _add_content('#---------- link ----------\n')
    for app_name, cpp_list in g_apps.items():
        obj_files = [_get_object_file(x) for x in cpp_list]
        _add_content_ext(app_name, 
                         False, 
                         obj_files,
                         ['$(CXX) %s $(LIBPATH) -o %s/bin/%s' % (' '.join(obj_files), g_output_dir, app_name)])
        _add_content('\n')

    for lib_name, (cpp_list, header_list) in g_libs.items():
        obj_files = [_get_object_file(x) for x in cpp_list]
        _add_content_ext(lib_name, 
                         False, 
                         obj_files,
                         ['ar crs %s/lib/%s %s' % (g_output_dir, lib_name, ' '.join(obj_files)),
                          'cp %s %s/include/' % (' '.join(header_list), g_output_dir)])
         
    _add_content('\n\n')

def _generate_compile_obj_part():
    _add_content('#---------- obj ----------\n')
    global g_cpps
    for cpp in g_cpps:
        obj_make_str = _get_single_obj_str(cpp)
        if None == obj_make_str:
            log_warning('handle cpp file error, file[%s]' % (cpp))
            sys.exit(1)
        _add_content(obj_make_str)
    _add_content('\n\n')

def _prepare():
    global g_apps 
    global g_cpps
    global g_protos
    global g_thrifts
    cpp_map = {}
    for proto in g_protos:
        targets = _generate_pb_files(proto)
        g_cpps.update(targets)
        cpp_map[proto] = targets
    for thrift in g_thrifts:
        targets = _generate_thrift_files(thrift)
        g_cpps.update(targets)
        cpp_map[thrift] = targets
    for app, targets in g_apps.items():
        new_targets = set() 
        for t in targets:
            if t.endswith('.proto') or t.endswith('.thrift'): 
                new_targets.update(cpp_map[t])    
            else:
                new_targets.add(t)
        g_apps[app] = new_targets

def generate_makefile():
    _prepare()
    _generate_env()
    _generate_phony()
    _generate_link_part()
    _generate_compile_obj_part()

def output():
    global g_content
    global g_output
    fp = open(g_output, 'w')
    fp.write(g_content)
    fp.close()

def show_help():
    print('this guy is lazy...')

def parse_args():
    global g_input
    global g_output
    global g_enable_update_deps
    opts, args = getopt.getopt(sys.argv[1:], "UBi:o:")
    for op, value in opts:
        if op == '-i':
            input_file = value
        elif op == '-o':
            output_file = value
        elif op == '-U':
            g_enable_update_deps = True
        elif op == '-h':
            show_help()
            sys.exit(0)

def update_deps():
    global g_deps
    global g_basedir
    for module, version in g_deps:
        module_path = g_basedir +  "/" + module
        log_notice('update module[%s:%s] path[%s]' % (module, version, module_path))
        if os.path.exists(module_path):
            os.system('rm -rf ' + module_path)
        ret = os.system('git clone -b %s https://github.com/tigerinsky/%s %s' % (version, module, module_path))
        if ret != 0:
            log_warning('get dependency error: module[%s] version[%s]' % (module, version))
            return 1
        if os.path.isfile(module_path + '/build.sh'):
            ret = os.system('cd %s && ./build.sh' % (module_path))
            if ret != 0:
                log_warning('build dependency error: module[%s] version[%s]' % (module, version))
                return 1

def dododo():
    global g_input
    global g_output
    global g_enable_update_deps
    
    execfile(g_input)

    if g_enable_update_deps:
        if update_deps():
            sys.exit(1)
        return

    generate_makefile()

    output()

def main():
    try:
        parse_args()
        dododo()
    except Exception, e:
        log_warning('exception occur: msg[%s]' % (e))
        sys.exit(1)

if __name__ == '__main__':
    main()

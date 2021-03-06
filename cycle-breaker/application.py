#!/usr/bin/env python3


# Cycle Breaker
# Copyright (C) 2017 Bjoern Griebenow <b.griebenow@web.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from enum import Enum
import argparse
import json
import os.path
import re
import sys


def pp(data):
    print(json.dumps(data, sort_keys=False, indent=4))


class LanguageBehavior():
    def read_file(self, source_filename):
        source_lines = []
        with open(source_filename) as source_file:
            for line_no, source_line in enumerate(source_file):
                source_lines.append({
                    'line_no': line_no,
                    'text':    source_line
                    })
        return source_lines

    def string_matches_least_one_in_regex_list(self, string_to_match, regex_list):
        for search_pattern in regex_list:
            if re.match(search_pattern, string_to_match):
                return True
        return False

    # TODO: Extract filename from reference line
    def extract_filename_from_source_line_by_regex_search(self, reference_line, regex_list):
        filename = dict(reference_line)
        for regex in regex_list:
            try:
                filename['target_filename'] = re.search(regex, reference_line['filtered_text']).group(1)
                return filename
            except AttributeError:
                continue
        raise ValueError("Cannot extract filename")

    def relative_filename_to_absolute_filename(self, relative_filename, global_options):
        return relative_filename

    def get_references_from_file(self, source_filename, global_options):
        """Fill a array with all found references."""
        source_lines = self.read_file(source_filename)
        active_source_lines = self.filter_inactive(source_lines)
        reference_lines = [_ for _ in active_source_lines if self.is_reference_string(_)]
        relative_reference_filenames = [self.extract_filename_from_source_line(_) for _ in reference_lines]
        references = [
            {
                'relative_filename': _['target_filename'],
                'absolute_filename': self.relative_filename_to_absolute_filename(_['target_filename'], global_options)
            } for _ in relative_reference_filenames
        ]
        return references


class CLanguageBehavior(LanguageBehavior):
    def is_reference_string(self, source_line):
        return self.string_matches_least_one_in_regex_list(source_line['filtered_text'], [r"^#include\ \""])

    # TODO: Detect multiline comments.
    def filter_inactive(self, source_lines):
        filtered_source_lines = []
        for source_line in source_lines:
            new_entry = dict(source_line)
            new_entry['filtered_text'] = re.sub(r"//.*$", "", source_line['text'])
            filtered_source_lines.append(new_entry)
        return filtered_source_lines
        # return [dict(_).update(['filtered_source_line'], re.sub(r"//.*$", "", _)) for _ in source_lines]

    # TODO: Extract filename from reference line
    def extract_filename_from_source_line(self, reference_line):
        return self.extract_filename_from_source_line_by_regex_search(reference_line, ['.*["<](.*)[">].*'])

    def system_reference_to_abs_filename(self, relative_filename):
        # TODO: Search at runtime with:
        # echo | gcc -E -Wp,-v - 2>&1 |grep " /usr"
        fixed_path_list = [
            '/usr/lib/gcc/x86_64-linux-gnu/6/include'
            '/usr/local/include'
            '/usr/lib/gcc/x86_64-linux-gnu/6/include-fixed'
            '/usr/include/x86_64-linux-gnu'
            '/usr/include'
        ]
        find_file_in_path_list(fixed_path_list, relative_filename)

    # FIXME Not used.
    def project_root_reference_to_abs_filename(self, relative_filename):
        raise NotImplementedError


class CppLanguageBehavior(LanguageBehavior):
    def is_reference_string(self, source_line):
        raise NotImplementedError

    def extract_filename_from_source_line(self, reference_line):
        raise NotImplementedError

    def system_reference_to_abs_filename(self, relative_filename):
        # TODO: Search at runtime with:
        # echo | cpp -xc++ -Wp,-v - 2>&1 |grep " /usr"
        fixed_path_list = [
            '/usr/include/c++/6',
            '/usr/include/x86_64-linux-gnu/c++/6',
            '/usr/include/c++/6/backward',
            '/usr/lib/gcc/x86_64-linux-gnu/6/include',
            '/usr/local/include',
            '/usr/lib/gcc/x86_64-linux-gnu/6/include-fixed',
            '/usr/include/x86_64-linux-gnu',
            '/usr/include'
        ]
        find_file_in_path_list(fixed_path_list, relative_filename)

    # FIXME Not used.
    def project_root_reference_to_abs_filename(self, relative_filename):
        # Should be identical to C.
        raise NotImplementedError
        # c_project_root_reference_to_abs_filename(relative_filename)


class ShellLanguageBehavior(LanguageBehavior):
    def is_reference_string(self, source_line):
        is_reference = self.string_matches_least_one_in_regex_list(source_line['filtered_text'],
                                                                   [r"^source ", r"^\.\ "])
        return is_reference

    # TODO: Detect multiline comments.
    def filter_inactive(self, source_lines):
        filtered_source_lines = []
        for source_line in source_lines:
            new_entry = dict(source_line)
            new_entry['filtered_text'] = re.sub(r"#.*$", "", source_line['text'])
            filtered_source_lines.append(new_entry)
        return filtered_source_lines

    def extract_filename_from_source_line(self, reference_line):
        extract_filename = dict(reference_line)
        filename = ""
        try:
            # Search for 'source' directive
            filename = re.search(r"^ *source +(.*)", reference_line['filtered_text']).group(1)
        except AttributeError:
            try:
                print("Try second extraction method")
                # Search for '.' directive
                filename = re.search(r"^\ *\.\ *(.+)", reference_line['filtered_text']).group(1)
            except AttributeError:
                raise ValueError("Cannot extract filename from string: ", reference_line['filtered_text'])

        filename_without_variables = re.sub(r"\${.*}/", "", filename).replace('"', '')
        extract_filename['target_filename'] = filename_without_variables
        return extract_filename

    # FIXME Not used.
    def project_root_reference_to_abs_filename(self, relative_filename):
        raise NotImplementedError


class PythonLanguageBehavior(LanguageBehavior):
    pass


class RubyLanguageBehavior(LanguageBehavior):
    pass


# {'search':             "#include <",
#  'filename_extract':   extract_filename_from_c_source,
#  'filename_fs_lookup': c_system_reference_to_abs_filename}

#     'cpp':    {'search':           ['#include '],
#                'filename_extract': extract_filename_from_cpp_source},
#     'python': {'search':           ['import '],
#                'filename_extract': extract_filename_from_python_source},
#     'ruby':   {'search':           ['require', 'require_local'],
#                'filename_extract': extract_filename_from_ruby_source}
# }


def find_file_in_path_list(path_list, relative_filename):
    for path in path_list:
        absolute_filename = os.path.join(path, relative_filename)
        if os.path.isfile(absolute_filename):
            return absolute_filename
    raise ValueError("File does not exist in any path:")


language_behaviour_mapping = {
    'c':      CLanguageBehavior(),
    'cpp':    CppLanguageBehavior(),
    'shell':  ShellLanguageBehavior(),
    'python': PythonLanguageBehavior(),
    'ruby':   RubyLanguageBehavior()
}


file_extension_language_mapping = {
    '.c':   'c',
    '.h':   'c',  # TODO: Can also map to C++
    '.cpp': 'cpp',
    '.hpp': 'cpp',
    '.sh':  'shell',
    '.py':  'python',
    '.rb':  'ruby'
}


def language_by_content(source_filename):
    """Detect programming language by file content."""
    with open(source_filename) as source_file_hdl:
        source = source_file_hdl.readlines()
        if '#!/bin/bash' in source[0]:
            return 'shell'
        if '#!/bin/sh' in source[0]:
            return 'shell'
        if 'python' in source[0]:
            return 'python'
        if 'ruby' in source[0]:
            return 'ruby'
    raise ValueError("Cannot detect programming language by source file content: " + source_filename)


def detect_programming_language(source_filename):
    file_extension = os.path.splitext(source_filename)[1]
    if file_extension == "":
        return language_by_content(source_filename)
    if file_extension not in file_extension_language_mapping:
        raise ValueError("File has unknown file extension: " + source_filename)
    return file_extension_language_mapping[file_extension]


def language_behaviour(language):
    if language not in language_behaviour_mapping:
        raise ValueError("Language has no string mapping: " + language)
    return language_behaviour_mapping[language]


def find_referenced_file_in_path_list(path_list, relative_filename):
    if len(path_list) == 0:
        raise ValueError("Empty path list given")
    for path in path_list:
        absolute_filename = os.path.join(path, relative_filename)
        if os.path.isfile(absolute_filename):
            return absolute_filename
    raise ValueError("Did not find referenced file in any path: "
                     + relative_filename)


def module_reference_filename_list(source_filename, global_options):
    ''' Search each source for a reference '''
    raise NotImplementedError
    # found_lines = []
    # filtered_file = c_filter_inactive(source_filename, global_options)
    # for line_no, line in enumerate(filtered_file):
    #     if re.match(search_pattern, line):
    #         relative_filename = language_behaviour_iter['filename_extract'](line)
    #         absolute_filename = find_referenced_file_in_path_list(
    #             global_options['project_include_path_list'], relative_filename)
    #         found_lines.append(absolute_filename)
    # return found_lines


def follow_module_references(source_filename,
                             recursion_history,
                             backtrace_recording,
                             global_options,
                             stats,
                             current_recursion_depth):
    new_recursion_history = set(recursion_history)
    new_recursion_history.add(source_filename)

    stats['file_check_cnt'] += 1
    if current_recursion_depth > stats['max_recursion_depth']:
        stats['max_recursion_depth'] = current_recursion_depth

    if source_filename in recursion_history:
        # print("Cycle found")
        backtrace_recording.append(source_filename)
        return 1

    if current_recursion_depth > global_options['max_recursion_depth']:
        # print("Maximum recursion exceeded: ", global_options['max_recursion_depth'])
        backtrace_recording.append(source_filename)
        return 2
    reference_list = global_options['language_behaviour'].get_references_from_file(source_filename,
                                                                                   global_options)
    for reference in reference_list:
        recursion_return_code = follow_module_references(reference['absolute_filename'],
                                                         new_recursion_history,
                                                         backtrace_recording,
                                                         global_options,
                                                         stats,
                                                         current_recursion_depth + 1)
        if recursion_return_code != 0:
            backtrace_recording.append(source_filename)
            return recursion_return_code
    return 0


def global_options_for_report(global_options):
    return {
        key: global_options[key] for key in [
            'start_source_filename',
            'project_include_path_list',
            'language',
            'max_recursion_depth',
            'json_report'
        ]
    }


def print_json_report(report_data):
    print(json.dumps(
        {
            'result':         report_data['result'],
            'global_options': global_options_for_report(report_data['global_options']),
            'stats':          report_data['stats'],
            'debug':          report_data['debug']
        },
        sort_keys=False, indent=4))


def print_human_readable_category_header(category_name):
    print('')
    print(category_name.upper(), ':', sep='')
    print('-' * 72)


def print_human_readable_report(report_data):
    print_human_readable_category_header('result')
    print("Cycle found:                  ", report_data['result']['cycle_found'])
    print("Cycle backtrace:              ", report_data['result']['cycle_backtrace'])

    print_human_readable_category_header('global options')
    print("Start filename:               ", report_data['global_options']['start_source_filename'])
    print("Language:                     ", report_data['global_options']['language'])
    print("Maximum search depth:         ", report_data['global_options']['max_recursion_depth'])
    print("Project include path list:    ", report_data['global_options']['project_include_path_list'])
    print("System include path list:     ", [])

    print_human_readable_category_header('statistics')
    print("Number of checked files:      ", report_data['stats']['file_check_cnt'])
    print("Highest occured search depth: ", report_data['stats']['max_recursion_depth'])

    print_human_readable_category_header('debug')
    print("Python recursion limit:       ", report_data['debug']['python_recursion_limit'])


def print_report(report_data):
    if report_data['global_options']['json_report']:
        print_json_report(report_data)
    else:
        print_human_readable_report(report_data)


def run_application(arguments):
    debug = {
        'python_recursion_limit': sys.getrecursionlimit()
    }

    cmd_line_parser = argparse.ArgumentParser(prog='cycle-parser')
    cmd_line_parser.add_argument("file",
                                 help="Source filename to start the search on.")
    cmd_line_parser.add_argument('-i', nargs=1, action='append', default=[["."]],
                                 help='Additional include path to look up relative source filenames. Can be used multiple times to add more than one path.',
                                 metavar='INCLUDE_PATH')
    cmd_line_parser.add_argument('-s', type=int, choices=range(1, debug['python_recursion_limit']), default=500,
                                 help='Maximum search depth before giving up. Default is 500, which is already insanely high.',
                                 metavar='SEARCH_DEPTH')
    cmd_line_parser.add_argument('-j', action='store_true',
                                 help='Print report as JSON object instead of a human readable format.')
    cmd_line_args = cmd_line_parser.parse_args(arguments[1:])

    project_include_path_array_list = cmd_line_args.i
    project_include_path_list = sum(project_include_path_array_list, [])
    start_source_filename = cmd_line_args.file

    language = detect_programming_language(start_source_filename)
    behaviour = language_behaviour(language)

    global_options = {
        'start_source_filename':     start_source_filename,
        'project_include_path_list': project_include_path_list,
        'language':                  language,
        'language_behaviour':        behaviour,
        'max_recursion_depth':       cmd_line_args.s,
        'json_report':               cmd_line_args.j
    }

    stats = {
        'file_check_cnt':      0,
        'max_recursion_depth': 0
    }

    recursion_history = set()
    backtrace_recording = []

    cycle_found = follow_module_references(start_source_filename,
                                           recursion_history,
                                           backtrace_recording,
                                           global_options,
                                           stats,
                                           0)

    result = {
        'cycle_found':     cycle_found,
        'cycle_backtrace': backtrace_recording
    }

    print_report({
        'result':         result,
        'global_options': global_options,
        'stats':          stats,
        'debug':          debug
    })

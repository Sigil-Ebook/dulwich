# patch.py -- For dealing with packed-style patches.
# Copyright (C) 2009-2013 Jelmer Vernooij <jelmer@jelmer.uk>
#
# Dulwich is dual-licensed under the Apache License, Version 2.0 and the GNU
# General Public License as public by the Free Software Foundation; version 2.0
# or (at your option) any later version. You can redistribute it and/or
# modify it under the terms of either of these two licenses.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# You should have received a copy of the licenses; if not, see
# <http://www.gnu.org/licenses/> for a copy of the GNU General Public License
# and <http://www.apache.org/licenses/LICENSE-2.0> for a copy of the Apache
# License, Version 2.0.
#

"""Classes for dealing with git am-style patches.

These patches are basically unified diffs with some extra metadata tacked
on.
"""

from difflib import SequenceMatcher
import email.parser
import time
import os
import hashlib

from dulwich.objects import (
    Blob,
    Commit,
    S_ISGITLINK,
    )

from dulwich.index import (
    changes_from_tree,
    changes_from_workingdir,
    os_sep_bytes
)

FIRST_FEW_BYTES = 8000


def write_commit_patch(f, commit, contents, progress, version=None,
                       encoding=None):
    """Write a individual file patch.

    Args:
      commit: Commit object
      progress: Tuple with current patch number and total.
    Returns:
      tuple with filename and contents
    """
    encoding = encoding or getattr(f, "encoding", "ascii")
    if isinstance(contents, str):
        contents = contents.encode(encoding)
    (num, total) = progress
    f.write(b"From " + commit.id + b" " +
            time.ctime(commit.commit_time).encode(encoding) + b"\n")
    f.write(b"From: " + commit.author + b"\n")
    f.write(b"Date: " +
            time.strftime("%a, %d %b %Y %H:%M:%S %Z").encode(encoding) + b"\n")
    f.write(("Subject: [PATCH %d/%d] " % (num, total)).encode(encoding) +
            commit.message + b"\n")
    f.write(b"\n")
    f.write(b"---\n")
    try:
        import subprocess
        p = subprocess.Popen(["diffstat"], stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE)
    except (ImportError, OSError):
        pass  # diffstat not available?
    else:
        (diffstat, _) = p.communicate(contents)
        f.write(diffstat)
        f.write(b"\n")
    f.write(contents)
    f.write(b"-- \n")
    if version is None:
        from dulwich import __version__ as dulwich_version
        f.write(b"Dulwich %d.%d.%d\n" % dulwich_version)
    else:
        f.write(version.encode(encoding) + b"\n")


def get_summary(commit):
    """Determine the summary line for use in a filename.

    Args:
      commit: Commit
    Returns: Summary string
    """
    decoded = commit.message.decode(errors='replace')
    return decoded.splitlines()[0].replace(" ", "-")


#  Unified Diff
def _format_range_unified(start, stop):
    'Convert range to the "ed" format'
    # Per the diff spec at http://www.unix.org/single_unix_specification/
    beginning = start + 1  # lines start numbering with one
    length = stop - start
    if length == 1:
        return '{}'.format(beginning)
    if not length:
        beginning -= 1  # empty ranges begin at line just before the range
    return '{},{}'.format(beginning, length)


def unified_diff(a, b, fromfile='', tofile='', fromfiledate='',
                 tofiledate='', n=3, lineterm='\n'):
    """difflib.unified_diff that can detect "No newline at end of file" as
    original "git diff" does.

    Based on the same function in Python2.7 difflib.py
    """
    started = False
    for group in SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        if not started:
            started = True
            fromdate = '\t{}'.format(fromfiledate) if fromfiledate else ''
            todate = '\t{}'.format(tofiledate) if tofiledate else ''
            yield '--- {}{}{}'.format(
                fromfile.decode("ascii"),
                fromdate,
                lineterm
                ).encode('ascii')
            yield '+++ {}{}{}'.format(
                tofile.decode("ascii"),
                todate,
                lineterm
                ).encode('ascii')

        first, last = group[0], group[-1]
        file1_range = _format_range_unified(first[1], last[2])
        file2_range = _format_range_unified(first[3], last[4])
        yield '@@ -{} +{} @@{}'.format(
            file1_range,
            file2_range,
            lineterm
             ).encode('ascii')

        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield b' ' + line
                continue
            if tag in ('replace', 'delete'):
                for line in a[i1:i2]:
                    if not line[-1:] == b'\n':
                        line += b'\n\\ No newline at end of file\n'
                    yield b'-' + line
            if tag in ('replace', 'insert'):
                for line in b[j1:j2]:
                    if not line[-1:] == b'\n':
                        line += b'\n\\ No newline at end of file\n'
                    yield b'+' + line


def is_binary(content):
    """See if the first few bytes contain any null characters.

    Args:
      content: Bytestring to check for binary content
    """
    return b'\0' in content[:FIRST_FEW_BYTES]


def shortid(hexsha):
    if hexsha is None:
        return b"0" * 7
    else:
        return hexsha[:7]


def patch_filename(p, root):
    if p is None:
        return b"/dev/null"
    else:
        return root + b"/" + p


def write_object_diff(f, store, old_file, new_file, diff_binary=False):
    """Write the diff for an object.

    Args:
      f: File-like object to write to
      store: Store to retrieve objects from, if necessary
      old_file: (path, mode, hexsha) tuple
      new_file: (path, mode, hexsha) tuple
      diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().

    Note: the tuple elements should be None for nonexistant files
    """
    (old_path, old_mode, old_id) = old_file
    (new_path, new_mode, new_id) = new_file
    patched_old_path = patch_filename(old_path, b"a")
    patched_new_path = patch_filename(new_path, b"b")

    def content(mode, hexsha):
        if hexsha is None:
            return Blob.from_string(b'')
        elif S_ISGITLINK(mode):
            return Blob.from_string(b"Subproject commit " + hexsha + b"\n")
        else:
            return store[hexsha]

    def lines(content):
        if not content:
            return []
        else:
            return content.splitlines()
    f.writelines(gen_diff_header(
        (old_path, new_path), (old_mode, new_mode), (old_id, new_id)))
    old_content = content(old_mode, old_id)
    new_content = content(new_mode, new_id)
    if not diff_binary and (
            is_binary(old_content.data) or is_binary(new_content.data)):
        binary_diff = (
            b"Binary files "
            + patched_old_path
            + b" and "
            + patched_new_path
            + b" differ\n"
        )
        f.write(binary_diff)
    else:
        f.writelines(unified_diff(lines(old_content), lines(new_content),
                     patched_old_path, patched_new_path))


# TODO(jelmer): Support writing unicode, rather than bytes.
def gen_diff_header(paths, modes, shas):
    """Write a blob diff header.

    Args:
      paths: Tuple with old and new path
      modes: Tuple with old and new modes
      shas: Tuple with old and new shas
    """
    (old_path, new_path) = paths
    (old_mode, new_mode) = modes
    (old_sha, new_sha) = shas
    if old_path is None and new_path is not None:
        old_path = new_path
    if new_path is None and old_path is not None:
        new_path = old_path
    old_path = patch_filename(old_path, b"a")
    new_path = patch_filename(new_path, b"b")
    yield b"diff --git " + old_path + b" " + new_path + b"\n"

    if old_mode != new_mode:
        if new_mode is not None:
            if old_mode is not None:
                yield ("old file mode %o\n" % old_mode).encode('ascii')
            yield ("new file mode %o\n" % new_mode).encode('ascii')
        else:
            yield ("deleted file mode %o\n" % old_mode).encode('ascii')
    yield b"index " + shortid(old_sha) + b".." + shortid(new_sha)
    if new_mode is not None and old_mode is not None:
        yield (" %o" % new_mode).encode('ascii')
    yield b"\n"


# TODO(jelmer): Support writing unicode, rather than bytes.
def write_blob_diff(f, old_file, new_file):
    """Write blob diff.

    Args:
      f: File-like object to write to
      old_file: (path, mode, hexsha) tuple (None if nonexisting)
      new_file: (path, mode, hexsha) tuple (None if nonexisting)

    Note: The use of write_object_diff is recommended over this function.
    """
    (old_path, old_mode, old_blob) = old_file
    (new_path, new_mode, new_blob) = new_file
    patched_old_path = patch_filename(old_path, b"a")
    patched_new_path = patch_filename(new_path, b"b")

    def lines(blob):
        if blob is not None:
            return blob.splitlines()
        else:
            return []
    f.writelines(gen_diff_header(
        (old_path, new_path), (old_mode, new_mode),
        (getattr(old_blob, "id", None), getattr(new_blob, "id", None))))
    old_contents = lines(old_blob)
    new_contents = lines(new_blob)
    f.writelines(unified_diff(old_contents, new_contents,
                 patched_old_path, patched_new_path))


def write_tree_diff(f, store, old_tree, new_tree, diff_binary=False):
    """Write tree diff.

    Args:
      f: File-like object to write to.
      old_tree: Old tree id
      new_tree: New tree id
      diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().
    """
    changes = store.tree_changes(old_tree, new_tree)
    for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in changes:
        write_object_diff(f, store, (oldpath, oldmode, oldsha),
                          (newpath, newmode, newsha), diff_binary=diff_binary)


def git_am_patch_split(f, encoding=None):
    """Parse a git-am-style patch and split it up into bits.

    Args:
      f: File-like object to parse
      encoding: Encoding to use when creating Git objects
    Returns: Tuple with commit object, diff contents and git version
    """
    encoding = encoding or getattr(f, "encoding", "ascii")
    encoding = encoding or "ascii"
    contents = f.read()
    if (isinstance(contents, bytes) and
            getattr(email.parser, "BytesParser", None)):
        parser = email.parser.BytesParser()
        msg = parser.parsebytes(contents)
    else:
        parser = email.parser.Parser()
        msg = parser.parsestr(contents)
    return parse_patch_message(msg, encoding)


def parse_patch_message(msg, encoding=None):
    """Extract a Commit object and patch from an e-mail message.

    Args:
      msg: An email message (email.message.Message)
      encoding: Encoding to use to encode Git commits
    Returns: Tuple with commit object, diff contents and git version
    """
    c = Commit()
    c.author = msg["from"].encode(encoding)
    c.committer = msg["from"].encode(encoding)
    try:
        patch_tag_start = msg["subject"].index("[PATCH")
    except ValueError:
        subject = msg["subject"]
    else:
        close = msg["subject"].index("] ", patch_tag_start)
        subject = msg["subject"][close+2:]
    c.message = (subject.replace("\n", "") + "\n").encode(encoding)
    first = True

    body = msg.get_payload(decode=True)
    lines = body.splitlines(True)
    line_iter = iter(lines)

    for line in line_iter:
        if line == b"---\n":
            break
        if first:
            if line.startswith(b"From: "):
                c.author = line[len(b"From: "):].rstrip()
            else:
                c.message += b"\n" + line
            first = False
        else:
            c.message += line
    diff = b""
    for line in line_iter:
        if line == b"-- \n":
            break
        diff += line
    try:
        version = next(line_iter).rstrip(b"\n")
    except StopIteration:
        version = None
    return c, diff, version


# To-Do handle line_ending conversion or 
# convert to use blob_from_path_and_stat
# along with a blob checkin / checkout normalizer
def _get_file_info(file_path):
    stat = os.lstat(file_path)
    fsize = stat.st_size 
    fmode = stat.st_mode
    h = hashlib.sha1()
    h.update(b'blob %d' % fsize + b'\0')
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(h.block_size)
            if not chunk:
                break
            h.update(chunk)
        hexsha = h.hexdigest().encode('ascii')
    return (hexsha, fmode)


def write_tree_workingdir_diff(f, store, tree, names, diff_binary=False):
    """Write diff of tree against current working dir

    Args:
      f: File-like object to write to.
      tree: tree id for base of comparison
      names: list of working directory relative file paths (bytes)
      diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().
    """

    entry_info = {}

    def lookup_entry(name):
        return entry_info.get(name, (None, None))

    for name in names:
        filepath = name
        if os_sep_bytes != b'/':
            filepath = name.replace(b'/', os_sep_bytes)
        entry_info[name] = _get_file_info(filepath)
    
    for change_entry in changes_from_tree(names, lookup_entry, store, tree):
        (name1, name2), (mode1, mode2), (sha1, sha2) = change_entry
        content1 = b''
        content2 = b''
        if name2:
            filepath = name2
            if os_sep_bytes != b'/':
                filepath = name2.replace(b'/', os_sep_bytes)
            with open(filepath, 'rb') as d:
                content2 = d.read()
            if name1:
                content1 = store[sha1].as_raw_string()
            if not name2:
                name2 = name1
            if not name1:
                name1 = name2
            old_path = patch_filename(name1, b"a")
            new_path = patch_filename(name2, b"b")
            f.write(b"diff --git " + old_path + b" " + new_path + b"\n")
            f.write(b"index " + shortid(sha1) + b".." + shortid(sha2) + b"\n")
            if is_binary(content1) or is_binary(content2):
                f.write(b"Binary files " + old_path + b" and " + new_path + b" differ\n")
            else:
                f.writelines(unified_diff(content1.splitlines(keepends=True),
                                          content2.splitlines(keepends=True), 
                                          old_path,
                                          new_path)
                             )


def write_tree_index_diff(f, store, tree, index, diff_binary=False):
    """Write diff of tree against current index

    Args:
      f: File-like object to write to.
      tree: tree id for base of comparison
      index: index (Index instance)
      diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().
    """
    from dulwich.index import Index
    for change_entry in index.changes_from_tree(store, tree):
        (name1, name2), (mode1, mode2), (sha1, sha2) = change_entry
        content1 = b''
        content2 = b''
        if name2:
            content2 = store[sha2].as_raw_string()
        if name1:
            content1 = store[sha1].as_raw_string()
        if not name2:
            name2 = name1
        if not name1:
            name1 = name2
        old_path = patch_filename(name1, b"a")
        new_path = patch_filename(name2, b"b")
        f.write(b"diff --git " + old_path + b" " + new_path + b"\n")
        f.write(b"index " + shortid(sha1) + b".." + shortid(sha2) + b"\n")
        if is_binary(content1) or is_binary(content2):
            f.write(b"Binary files " + old_path + b" and " + new_path + b" differ\n")
        else:
            f.writelines(unified_diff(content1.splitlines(keepends=True),
                                      content2.splitlines(keepends=True), 
                                      old_path,
                                      new_path)
                         )



def write_index_workingdir_diff(f, store, index, names, diff_binary=False):
    """Write diff of index against current working dir

    Args:
      f: File-like object to write to.
      index: Index object for base of comparison
      names: list of working directory relative file paths (bytes)
      diff_binary: Whether to diff files even if they
        are considered binary files by is_binary().
    """

    entry_info = {}

    def lookup_entry(name):
        return entry_info.get(name, (None, None))

    for name in names:
        filepath = name
        if os_sep_bytes != b'/':
            filepath = name.replace(b'/', os_sep_bytes)
        entry_info[name] = _get_file_info(filepath)
    
    for change_entry in changes_from_workingdir(names, lookup_entry, store, index):
        (name1, name2), (mode1, mode2), (sha1, sha2) = change_entry
        content1 = b''
        content2 = b''
        if name2:
            filepath = name2
            if os_sep_bytes != b'/':
                filepath = name2.replace(b'/', os_sep_bytes)
            with open(filepath, 'rb') as d:
                content2 = d.read()
            if name1:
                content1 = store[sha1].as_raw_string()
            if not name2:
                name2 = name1
            if not name1:
                name1 = name2
            old_path = patch_filename(name1, b"a")
            new_path = patch_filename(name2, b"b")
            f.write(b"diff --git " + old_path + b" " + new_path + b"\n")
            f.write(b"index " + shortid(sha1) + b".." + shortid(sha2) + b"\n")
            if is_binary(content1) or is_binary(content2):
                f.write(b"Binary files " + old_path + b" and " + new_path + b" differ\n")
            else:
                f.writelines(unified_diff(content1.splitlines(keepends=True),
                                          content2.splitlines(keepends=True), 
                                          old_path,
                                          new_path)
                             )

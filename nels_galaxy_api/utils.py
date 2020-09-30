import os

from Crypto.Cipher import Blowfish
from Crypto.Random import get_random_bytes
import codecs

import kbr.file_utils as file_utils
import re

id_cipher = None

def init( id_secret:str) -> None:
    global id_cipher
    id_cipher = Blowfish.new(id_secret.encode('utf-8'), mode=Blowfish.MODE_ECB)


def decrypt_value(value:str) -> str:
    value = str(value)
    value_hex = codecs.decode(value, 'hex')
    decrypted_value = id_cipher.decrypt( value_hex ).decode("utf-8").lstrip("!")
    return decrypted_value

def encrypt_value(value:str) -> str:
    value = str(value)
    value = value.encode('utf-8')
    s = (b"!" * (8 - len(value) % 8)) + value
    # Encrypt
    return codecs.encode(id_cipher.encrypt(s), 'hex').decode("utf-8")

def directory_hash_id(id):
    s = str(id)
    l = len(s)
    # Shortcut -- ids 0-999 go under ../000/
    if l < 4:
        return ["000"]
    # Pad with zeros until a multiple of three
    padded = ((3 - len(s) % 3) * "0") + s
    # Drop the last three digits -- 1000 files per directory
    padded = padded[:-3]
    # Break into chunks of three
    return [padded[i * 3:(i + 1) * 3] for i in range(len(padded) // 3)]

def construct_file_path(obj_id, file_dir=None):
    """
    Taken and adjusted from the galaxy code base.
    Construct the absolute path for accessing the object identified by `obj_id`.

    :type file_dir: string
    :param file_dir: A key in self.extra_dirs corresponding to the base
                     directory in which this object should be created, or
                     None to specify the default directory.

     This option is used for backward compatibility. If
                    `True` then the composed directory structure does not include a
                     hash id (e.g., /files/dataset_10.dat (old) vs.
                     /files/000/dataset_10.dat (new))
    """
#    base = os.path.abspath(file_dir, self.file_path))
    base = file_dir
    # extra_dir should never be constructed from provided data but just
    # make sure there are no shenannigans afoot

    # Construct hashed path
    rel_path = os.path.join(*directory_hash_id(obj_id))
    # Create a subdirectory for the object ID
    path = os.path.join(base, rel_path)
    path = os.path.join(path, "dataset_%s.dat" % obj_id)
    if os.path.isfile(path):
        return path

    #Try old style dir names:

    path = base
    path = os.path.join(path, "dataset_%s.dat" % obj_id)
    if os.path.isfile( path ):
        return path


    path = file_utils.find_first("dataset_%s.dat" % obj_id, file_dir)
    if path is not None:
        return path

    raise RuntimeError(f"Cannot find dataset: 'dataset_{obj_id}.dat'")


def create_uuid(length=16):
    # Generate a unique, high entropy random number.
    # Length 16 --> 128 bit
    long_uuid = codecs.encode(get_random_bytes(length), 'hex').decode("utf-8")
    return long_uuid[:32]

def encrypt_ids(entry: any) -> []:
    if isinstance(entry, list):
        return list_encrypt_ids(entry)

    if entry == [] or entry == {}:
        return entry

    if isinstance(entry, dict):
        for key in entry.keys():
            if key == 'nels_id':
                continue

            if key == 'id' or key.find('_id') > -1 and isinstance(entry[key], int):
                entry[f"{key}"] = encrypt_value(entry[key])

    else:
        raise RuntimeError(f"Cannot change ids in {entry}")

    return entry


def list_encrypt_ids(entries: []) -> []:
    for entry in entries:
        entry = encrypt_ids(entry)

    return entries

def readable_date(timestamp:str) -> str:

    if timestamp is None:
        return None

    timestamp = timestamp.replace('T', ' ')
    timestamp = re.sub(r'\.\d+', '', timestamp)

    return timestamp

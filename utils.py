# Roni Oded 318798782, Eden Cohen 318758778
# imports.
import os

# global variables.
SEPARATOR = "<SEPARATOR>"
BUFFER = 4096


'''
the function will normalize the path specific to the operating system.
@path- the path to convert.
'''


def normalize_path(path):
    # normalize the path as the operating system.
    if os.name == 'nt':
        return path.replace('/', '\\')
    else:
        return path.replace('\\', '/')


'''
the function responsible on send all bytes in a file.
@file_path - the path of the file.
@root_path - the path of the directory register to the service.
@s - the socket.
'''


def send_file(file_path, root_path, s):
    # extract the relative path and the file size.
    try:
        path_to_send = file_path.split(root_path)[1]
    except (Exception,):
        path_to_send = file_path

    file_size = os.path.getsize(file_path)
    # send the path and the file size and wait for ack.
    s.send(f"{path_to_send}{SEPARATOR}{file_size}".encode())
    ack = s.recv(3)
    # send to the other size that the package is a file.
    s.send('1'.encode())
    try:
        # open the file and reading its bytes.
        with open(file_path, "rb") as f:
            while True:
                # read the content.
                read_content = f.read(BUFFER)

                # if there is no more content, break the loop.
                if not read_content:
                    ack = s.recv(3)
                    break
                # send the content.
                s.send(read_content)
    except (Exception,):
        pass
    # close the file.
    f.close()


'''
the function responsible on send directory.
@dir_path - the path of the dir.
@s - the socket.
'''


def send_dir(dir_path, s):
    # send to the server the dir path and wait for ack.
    s.send(f"{dir_path}{SEPARATOR}{0}".encode())
    ack = s.recv(3)

    # send 0 in order to announce this is a dir and not a file.
    s.send('0'.encode())


'''
the function responsible on sending all files and dirs in a directory
@root_path - the dir to send all files from.
@s - the socket.
'''


def send_all_content(root_path, s):
    # passing the files and dirs in root_path and send each file or dir via the socket.
    for (root, dirs, files) in os.walk(root_path, topdown=True):
        # send the files via the socket.
        for file in files:
            send_file(os.path.join(root, file), root_path, s)

        # send the dirs via the socket.
        for directory in dirs:
            send_dir(os.path.join(root, directory).split(root_path)[1], s)

    # send via the socket we are done sending the content and wait for ack.
    s.send(f"{'done'}{SEPARATOR}{0}".encode())
    ack = s.recv(3)


'''
the function receive content via the socket and creating all of it in the root_path.
@root_path - where to create the content.
@s - the socket.
'''


def create_all_content(root_path, s):
    # receive path and file size, normalize the path and send ack.
    content = s.recv(BUFFER).decode()
    received_path, file_size = content.split(SEPARATOR)
    received_path = normalize_path(received_path)
    s.send("ack".encode())

    # while the path is not equal to done, receive files and dirs.
    while received_path != 'done':
        # combine the received path to the root path and create file or dir via the function responsible for it.
        combined_path = root_path + received_path
        check_create_file_dir(file_size, combined_path, s)

        # receive a new path and file size, normalize the path and send ack.
        content = s.recv(BUFFER).decode()
        received_path, file_size = content.split(SEPARATOR)
        received_path = normalize_path(received_path)
        s.send("ack".encode())


'''
the function responsible of creating a file or dir.
@file_size - the file size.
@combined_path - the path to create.
@s - the socket.
'''


def check_create_file_dir(file_size, combined_path, s):
    # receive via the socket whether the package is file or directory
    is_file = s.recv(1).decode()

    # if the data is file, create new file.
    if is_file == '1':
        create_file(combined_path, file_size, s)

    # if it is a folder, create new folder.
    else:
        os.mkdir(combined_path)


'''
the function create a file with all the content received via the socket.
@combined_path - the path to create.
@file_size - the file size.
@s - the socket.
'''


def create_file(combined_path, file_size, s):
    # initializing num of bytes received.
    num_received = 0
    try:
        # create new file, and write the received content to it.
        with open(combined_path, "wb") as f:
            while True:
                # if the num_received is bigger or equal to file_size, we are done receiving the content so send ack and
                # break the loop.
                if num_received >= int(file_size):
                    s.send("ack".encode())
                    break

                # receive a new package, add the len of the content to num_received and write to the file.
                received_content = s.recv(BUFFER)
                num_received += len(received_content)
                f.write(received_content)
        # close the file.
        f.close()
    except (Exception,):
        pass


'''
the function is fulfill a create request after monitoring changes.
@combined_path - the path to create.
@file_size - the file size.
@s - the socket.
'''


def create(combined_path, file_size, s):
    # flag that represent if we delete what in the path or not.
    flag = False

    # if it is existed, then delete first.
    if os.path.exists(combined_path):
        delete(combined_path)
        flag = True
    # receive via the socket whether the package is file or directory
    is_file = s.recv(1).decode()

    # if the data is file, create new file.
    if is_file == '1':
        create_file(combined_path, file_size, s)

    # if this is a folder, create new folder, and receive all content in the folder too.
    else:
        try:
            os.mkdir(combined_path)
            create_all_content(combined_path, s)
        except (Exception,):
            pass
    # first flag represent that we need to add the change to the dictionary. second flag represent if we deleted first.
    return True, flag


'''
the function is fulfill a delete request after monitoring changes.
@combined_path - the path to create.
'''


def delete(combined_path):
    # deleting only if it is existed.
    if os.path.exists(combined_path):
        # if it is a file then delete file.
        if os.path.isfile(combined_path):
            os.remove(combined_path)

        # else, remove a directory and all the content inside.
        else:
            delete_full_directory(combined_path)
        # first flag represent that we need to add the change to the dictionary. second flag represent that we do not
        # want to add delete to the dictionary cause this is already delete.
        return True, False
    # first flag represent that we need to add the change to the dictionary. second flag represent that we do not want
    # to add delete to the dictionary.
    return False, False


'''
the function is fulfill a modify request after monitoring changes.
@combined_path - the path to create.
@file_size - the file size.
@s - the socket.
'''


def modify(combined_path, file_size, s):
    # delete and then create new.
    delete(combined_path)
    check_create_file_dir(file_size, combined_path, s)
    # first flag represent that we need to add the change to the dictionary. second flag represent that we do not want
    # to add delete to the dictionary.
    return True, True


'''
the function is fulfill a moved request after monitoring changes.
@src_path - the path to delete from.
@dst_size - the path to create in.
@s - the socket.
@return- 
first boolean return represent if we need to add the change to the dictionary.
second boolean return represent if we need to delete the src_path.
third boolean return represent if we need to delete the dst_path.
'''


def moved(src_path, dst_path, s):
    # flag1 represent if we need to add the change to the dictionary.
    # flag2 represent if we need to delete the src_path.
    # flag3 represent if we need to delete the dst_path.
    flag1 = False
    flag2 = False
    flag3 = False

    # delete the src path, flag2 represent if we deleted the src_path.
    flag2, flag = delete(src_path)

    if flag2:
        # send to the other side that we need to send the whole file.
        s.send('1'.encode())

        # receive the file size (and received_path too because it comes together).
        content = s.recv(BUFFER).decode()
        s.send("ack".encode())
        received_path, file_size = content.split(SEPARATOR)

        # create the file in dst_path.
        # flag1 represent if we need to add the dictionary, so if create return that we need to add, also this
        # return that. flag3 represent if we deleted the src_path, so if create return true on that, also this
        # return that.
        flag1, flag3 = create(dst_path, file_size, s)
    # send to the other side that we do not need to send the whole file.
    s.send('0'.encode())
    # return the flags.
    return flag1, flag2, flag3


'''
the function delete all content inside the root_path and in the end the root too.
@root_path - the dir to delete.
'''


def delete_full_directory(root_path):
    # passing the objects in the dir.
    for ob in os.listdir(root_path):
        all_file = os.path.join(root_path, ob)
        # if it is a file, then delete the file.
        if os.path.isfile(all_file):
            os.remove(all_file)
        # else, delete all directory.
        else:
            delete_full_directory(all_file)
    # remove the root_path because we deleted all the content inside.
    os.rmdir(root_path)


'''
the function send file or dir.
@path - the path of the file or dir.
@root_path
@s- the socket.
'''


def file_or_dir(path, root_path, s):
    # if this is a file, then use send file function.
    if os.path.isfile(path):
        send_file(path, root_path, s)
    # else, use send dir function and then send all te files in the dir.
    else:
        split_path = path.split(root_path)[1]
        send_dir(split_path, s)
        send_all_content(path, s)

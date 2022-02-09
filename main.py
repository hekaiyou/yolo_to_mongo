import re
import os
import sys
import time
import hashlib
import pymongo
from PIL import Image
from datetime import datetime
from prompt_toolkit import HTML, prompt, PromptSession, print_formatted_text
from bson.objectid import ObjectId
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import yes_no_dialog, ProgressBar

bottom_remind = None


def set_bottom_toolbar(remind):
    global bottom_remind
    bottom_remind = remind


def get_bottom_toolbar():
    if bottom_remind:
        return HTML(bottom_remind)
    else:
        return HTML('欢迎使用 <b><style bg="ansired">YOLO</style> to <style bg="ansigreen">MongoDB</style></b> !')


def mongo_connection_validator(text):
    re_text = re.search(
        r'((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}:\d{5}',
        text,
        flags=0,
    )
    if not re_text:
        set_bottom_toolbar(
            f'测试 <b><style bg="ansired">{text}</style></b> 读写失败: <i>请参照 127.0.0.1:27017 格式输入</i>')
        return False
    try:
        client = pymongo.MongoClient(
            f'mongodb://{re_text.group()}/',
            serverSelectionTimeoutMS=3000,
            socketTimeoutMS=3000,
        )
        db = client['yolo_to_mongo']
        collection = db['test']
        result = collection.insert_one({'title': 'Python Connect MongoDB',
                                        "content": "Beautiful", "date": datetime.now()})
        for obj in collection.find({'_id': ObjectId(result.inserted_id)}):
            obj.pop('_id')
            set_bottom_toolbar(
                f'测试 <b><style bg="ansigreen">{re_text.group()}</style></b> 读写成功: <i>{obj}</i>')
        # 第一个参数找到要更新的文档, 后面是要更新的数据
        # collection.update({name: "xxx"}, {name: "XXX", args: ...})
        # 删除集合中的全部数据, 但是集合依然存在, 索引也在
        collection.delete_one({'_id': ObjectId(result.inserted_id)})
        # 删除集合 collection
        # collection.drop()
    except Exception as err:
        set_bottom_toolbar(
            f'测试 <b><style bg="ansired">{re_text.group()}</style></b> 读写失败: <i>{err}</i>')
        return False
    return True


def import_directory_validator(text):
    if not os.path.isdir(text):
        set_bottom_toolbar(
            f'验证目录 <b><style bg="ansired">{text}</style></b> 失败: <i>不存在的目录</i>')
        return False
    file_list = os.listdir(text)
    if not len(file_list) >= 3:
        set_bottom_toolbar(
            f'验证目录 <b><style bg="ansired">{text}</style></b> 失败: <i>至少需要 3 个文件</i>')
        return False
    if not 'classes.txt' in file_list:
        set_bottom_toolbar(
            f'验证目录 <b><style bg="ansired">{text}</style></b> 失败: <i>缺少 classes.txt 文件</i>')
        return False
    with open(os.path.join(text, 'classes.txt'), 'r') as f:
        classes_text = f.read()
    # print(classes_text.split('\n'))
    set_bottom_toolbar(
        f'验证目录 <b><style bg="ansigreen">{text}</style></b> 成功: <i>共有 {len(file_list)} 个文件和目录</i>')
    return True


def preprocess_label_data(import_file_directory):
    with open(os.path.join(import_file_directory, 'classes.txt'), 'r') as f:
        classes_text = f.read()
    classes_list = classes_text.split('\n')
    label_dict = {}
    for i in range(len(classes_list)):
        if classes_list[i]:
            label_dict[i] = classes_list[i]
    return label_dict


def preprocess_annotation_data(import_file_directory, label_dict):
    annotation_data = []
    file_list = os.listdir(import_file_directory)
    title = HTML(
        f'筛选目录下 <style bg="yellow" fg="black">{len(file_list)} 个文件...</style> 中的有效标注数据')
    label = HTML('<i>文件遍历进度</i>: ')
    with ProgressBar(title=title) as pb:
        for i in pb(file_list, label=label):
            if '.txt' in i:
                with open(os.path.join(import_file_directory, i), 'r') as f:
                    annotation_text = f.read()
                if annotation_text.split('\n'):
                    annotation_info_list = []
                    for annotation_str in annotation_text.split('\n'):
                        annotation_info = annotation_str.split(' ')
                        if len(annotation_info) == 5:
                            annotation_info_list.append({
                                'class': int(annotation_info[0]),
                                'label': label_dict[int(annotation_info[0])],
                                'info': annotation_info[1:],
                            })
                    if annotation_info_list:
                        if f'{i.split(".")[0]}.jpg' in file_list:
                            annotation_data.append({
                                'annotation': annotation_info_list,
                                'file': os.path.join(import_file_directory, f'{i.split(".")[0]}.jpg'),
                            })
    print_formatted_text(
        HTML(f'<ansigreen>共筛选出 <b>{len(annotation_data)}</b> 个有效标注数据</ansigreen>'))
    return annotation_data


def process_imported_data(annotation_data):
    imported_data = []
    title = HTML(
        f'处理待导入的 <style bg="yellow" fg="black">{len(annotation_data)} 个标注数据...</style> ({sys.getdefaultencoding()} 编码)')
    label = HTML('<i>数据处理进度</i>: ')
    with ProgressBar(title=title) as pb:
        for i in pb(annotation_data, label=label):
            # 以二进制形式读取文件数据
            with open(i['file'], 'rb') as f:
                file_data = f.read()
            file_md5 = hashlib.md5(file_data).hexdigest()
            i['file_md5'] = file_md5  # 图片文件MD5字符串
            i['file_byte_size'] = os.path.getsize(i['file'])  # 图片文件字节大小
            img = Image.open(i['file'])
            i['file_width'] = img.width  # 图片文件宽度
            i['file_height'] = img.height  # 图片文件高度
            i['file_mode'] = img.mode  # 图片文件像素格式
            imported_data.append(i)
    return imported_data


def main():
    session = PromptSession()
    print_formatted_text(HTML(
        '欢迎使用 <b><ansired>YOLO</ansired> <ansiyellow>to</ansiyellow> <ansigreen>MongoDB</ansigreen></b>'))
    while True:
        try:
            set_bottom_toolbar('待导入的图资和标注目录')
            import_file_directory = session.prompt(
                '> ',
                validator=Validator.from_callable(
                    import_directory_validator,
                    error_message='无效路径',
                    move_cursor_to_end=True,
                ),
                bottom_toolbar=get_bottom_toolbar,
            )
            set_bottom_toolbar('MongoDB 连接 HOST:PORT')
            mongo_host_port = session.prompt(
                '> ',
                validator=Validator.from_callable(
                    mongo_connection_validator,
                    error_message='无效地址',
                    move_cursor_to_end=True,
                ),
                bottom_toolbar=get_bottom_toolbar,
            )
            whether_to_start = yes_no_dialog(
                title='Yes/No 是否开始导入',
                text=f'待导入的图资和标注目录:\n    {import_file_directory}\nMongoDB 连接 HOST:PORT:\n    {mongo_host_port}',
            ).run()
            if whether_to_start:
                label_dict = preprocess_label_data(import_file_directory)
                annotation_data = preprocess_annotation_data(
                    import_file_directory, label_dict)
                imported_data = process_imported_data(annotation_data)
                print(imported_data[0])
        except KeyboardInterrupt:
            print_formatted_text(HTML(f'<b>安全退出</b>'))
            break


if __name__ == '__main__':
    main()

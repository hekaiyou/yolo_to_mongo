import re
import os
import sys
import logging
import hashlib
import pymongo
from PIL import Image, UnidentifiedImageError
from datetime import datetime
from prompt_toolkit import HTML, PromptSession, print_formatted_text
from bson.objectid import ObjectId
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import yes_no_dialog, ProgressBar

logging.basicConfig(
    level=logging.INFO,  # 控制台打印的日志级别
    filename='yolo_to_mongo.log',
    filemode='a',  # w:写模式,每次都会覆盖之前的日志;a:追加模式.默认如果不写的话,就是追加模式
    format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
)

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
    logging.info(f'导入标签字典: {label_dict}')
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
    logging.info(f'初筛标注数量: {len(annotation_data)}')
    return annotation_data


def process_imported_data(annotation_data):
    imported_data = []
    md5_list = []
    repeat_md5_list = []
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
            if file_md5 not in md5_list:
                md5_list.append(file_md5)
            else:
                repeat_md5_list.append({'md5': file_md5, 'file': i['file']})
            i['file_byte_size'] = os.path.getsize(i['file'])  # 图片文件字节大小
            try:
                img = Image.open(i['file'])
                i['file_width'] = img.width  # 图片文件宽度
                i['file_height'] = img.height  # 图片文件高度
                i['file_mode'] = img.mode  # 图片文件像素格式
            except UnidentifiedImageError:
                # 含有标注信息的图片无法被打开
                i['file_width'] = 0
                i['file_height'] = 0
                i['file_mode'] = ''
            imported_data.append(i)
    if repeat_md5_list:
        print_formatted_text(HTML(
            f'<ansiyellow>请注意, 出现 <b>{len(repeat_md5_list)}</b> 个重复 MD5 码的文件</ansiyellow>'))
        for repeat_md5 in repeat_md5_list:
            print_formatted_text(
                HTML(f'    <i><u>{repeat_md5["file"]}</u></i>'))
    else:
        print_formatted_text(HTML(
            f'<ansigreen>完成 <b>{len(imported_data)}</b> 个数据的处理, 没有出现重复 MD5 码</ansigreen>'))
    logging.info(f'重复MD5编号: {len(repeat_md5_list)}')
    logging.info(f'有效标注数量: {len(imported_data)}')
    return imported_data


def import_data(imported_data, mongo_host_port, whether_to_cover):
    already_exists = 0
    already_covered = 0
    client = pymongo.MongoClient(
        f'mongodb://{mongo_host_port}/',
        serverSelectionTimeoutMS=6000,
        socketTimeoutMS=6000,
    )
    db = client['yolo_to_mongo']
    collection = db['annotations']
    title = HTML(
        f'导入 <style bg="yellow" fg="black">{len(imported_data)} 个历史标注...</style> 到 MongoDB 数据库')
    label = HTML('<i>数据导入进度</i>: ')
    with ProgressBar(title=title) as pb:
        for i in pb(imported_data, label=label):
            find_result = collection.find_one({
                'file_md5': i['file_md5'], 'file_width': i['file_width'],
                'file_height': i['file_height'], 'file_mode': i['file_mode']
            })
            if find_result:
                annotate_exists = []  # 已存在的标框位置
                for annotate in find_result['annotation']:
                    annotate_exists.append(annotate['info'])
                for annotate in i['annotation']:
                    if annotate['info'] not in annotate_exists:
                        find_result['annotation'].append(annotate)
                if len(annotate_exists) != len(find_result['annotation']):
                    # 兼容同一张图片重复标注的情况
                    collection.update_one(
                        {'_id': ObjectId(find_result['_id'])},
                        {'$set': {'annotation': find_result['annotation']}}
                    )
                else:
                    if whether_to_cover:
                        collection.update_one(
                            {'_id': ObjectId(find_result['_id'])},
                            {'$set': {'annotation': i['annotation']}}
                        )
                        already_covered += 1
                    else:
                        already_exists += 1
            else:
                collection.insert_one(i)
    if whether_to_cover:
        print_formatted_text(HTML(
            f'<ansigreen>成功导入 <b>{len(imported_data)-already_exists}</b> 个数据, 覆盖 <b>{already_covered}</b> 个已存在数据</ansigreen>'))
    else:
        print_formatted_text(HTML(
            f'<ansigreen>成功导入 <b>{len(imported_data)-already_exists}</b> 个数据, 跳过 <b>{already_exists}</b> 个已存在数据</ansigreen>'))
    logging.info(
        f'导入总数: {len(imported_data)-already_exists}, 覆盖数: {already_covered}, 跳过数: {already_exists}')


def main():
    session = PromptSession()
    print_formatted_text(HTML(
        '欢迎使用 <b><ansired>YOLO</ansired> <ansiyellow>to</ansiyellow> <ansigreen>MongoDB</ansigreen></b>'))
    print_formatted_text(HTML(f'开始导入任务 <i>(按 Ctrl+C 安全退出)</i>'))
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
                logging.info(f'开始导入目录: {import_file_directory}')
                label_dict = preprocess_label_data(import_file_directory)
                annotation_data = preprocess_annotation_data(
                    import_file_directory, label_dict)
                imported_data = process_imported_data(annotation_data)
                whether_to_cover = yes_no_dialog(
                    title='Yes/No 是否覆盖已存在数据',
                    text=f'当导入数据在数据库中已经存在时, 是否覆盖写入 ?',
                ).run()
                import_data(imported_data, mongo_host_port, whether_to_cover)
            print_formatted_text(
                HTML(f'开始 <b><ansiyellow>下一轮</ansiyellow></b> 导入任务 <i>(按 Ctrl+C 安全退出)</i>'))
        except KeyboardInterrupt:
            print_formatted_text(HTML(f'<b>安全退出</b>'))
            break


if __name__ == '__main__':
    main()

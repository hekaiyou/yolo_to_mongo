import re
import os
import pymongo
from datetime import datetime
from prompt_toolkit import HTML
from prompt_toolkit import prompt
from bson.objectid import ObjectId
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator
from prompt_toolkit.shortcuts import yes_no_dialog

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


def main():
    session = PromptSession()
    while True:
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
            pass


if __name__ == '__main__':
    main()

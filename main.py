import re
import os
import pymongo
from datetime import datetime
from prompt_toolkit import prompt
from bson.objectid import ObjectId
from prompt_toolkit.validation import Validator
from prompt_toolkit import print_formatted_text


def mongo_connection_validator(text):
    re_text = re.search(
        r'((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}:\d{5}',
        text,
        flags=0,
    )
    if not re_text:
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
            print_formatted_text(f'测试 {re_text.group()} 读写成功: {obj}')
        # 第一个参数找到要更新的文档, 后面是要更新的数据
        # collection.update({name: "xxx"}, {name: "XXX", args: ...})
        # 删除集合中的全部数据, 但是集合依然存在, 索引也在
        collection.delete_one({'_id': ObjectId(result.inserted_id)})
        # 删除集合 collection
        # collection.drop()
    except Exception as err:
        print_formatted_text(f'测试 {re_text.group()} 读写失败: {err}')
        return False
    return True


def import_directory_validator(text):
    if not os.path.isdir(text):
        return False
    if len(os.listdir(text)) >= 2:
        print_formatted_text(f'验证目录 {text} 成功: 共有 {len(os.listdir(text))} 个文件')
    else:
        print_formatted_text(f'验证目录 {text} 失败: 至少需要2个文件')
        return False
    return True


def main():
    import_file_directory = prompt(
        '待导入的图资和标注目录 > ',
        validator=Validator.from_callable(
            import_directory_validator,
            error_message='请输入有效的目录绝对路径',
            move_cursor_to_end=True,
        ),
    )
    mongo_host_port = prompt(
        'MongoDB 连接 HOST:PORT > ',
        validator=Validator.from_callable(
            mongo_connection_validator,
            error_message='请参照 127.0.0.1:27017 格式输入',
            move_cursor_to_end=True,
        ),
    )


if __name__ == '__main__':
    main()

import re
import pymongo
from datetime import datetime
from prompt_toolkit import prompt
from pygments import lex
from pygments.lexers.jslt import JSLTLexer
from prompt_toolkit.validation import Validator
from prompt_toolkit import print_formatted_text


def mongo_connection_validator(text):
    re_text = re.search(
        r'((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}:\d{5}',
        text, flags=0,
    )
    if not re_text:
        return False
    client = pymongo.MongoClient(f'mongodb://{re_text.group()}/')
    db = client['yolo_to_mongo']
    collection = db['test']
    collection.insert({'title': 'python connect mongo',
                       "content": "beautiful", "date": datetime.now()})
    for obj in collection.find():
        obj_json = lex(obj, lexer=JSLTLexer())
        print_formatted_text('Find Test:', obj_json)
    # 第一个参数找到要更新的文档, 后面是要更新的数据
    # collection.update({name: "xxx"}, {name: "XXX", args: ...})
    # 删除集合中的全部数据, 但是集合依然存在, 索引也在
    collection.remove()
    # 删除集合 collection
    # collection.drop()
    return True


def main():
    mongo_connection = Validator.from_callable(
        mongo_connection_validator,
        error_message='This input contains non-numeric characters',
        move_cursor_to_end=True,
    )
    text = prompt('> ', validator=mongo_connection)
    print('You entered:', text)


if __name__ == '__main__':
    main()

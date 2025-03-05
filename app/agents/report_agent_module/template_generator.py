

class ResultTemplate:
    def __init__(self):
        
        self.template=self.default_template()
        self.generator = self.TemplateGenerator(self.template)
        self.dict_NONE = self.generator.dict()
        self.dict = self.generator.dict()
        
        
    @staticmethod
    def default_template():
        original_structure = {
            "product": {
                "name": None,            
                "category": None,     
                "recommendation": {
                    "main_reason": None,
                    "sub_reason": None,       
                    "good_person": [],         
                    "bad_person": []
                },
                "specifications": {
                    "display": {
                        "size": None,
                        "resolution": None,
                        "refresh_rate": None,
                        "description": None
                    },
                    "processor": {
                        "model": None,
                        "equivalent": None,
                        "description": None
                    },
                    "storage": {
                        "options": [],
                        "expandable": None,
                        "description": None
                    },
                    "battery": {
                        "capacity": None,
                        "description": None
                    },
                    "design": {
                        "features": [],
                        "description": None
                    },
                    "color_options": [],
                    "pencil_support": {
                        "supported": None,
                        "charging": None,
                        "description": None
                    },
                    "charging_port": {
                        "type": None,
                        "limitation": None,
                        "description": None
                    }
                }
            },
            "reviews": {
                "youtuber": {
                    "name": None,
                    "subscribers": None,
                    "review_video": {
                        "title": None,
                        "views": None,
                        "time_since_upload": None,
                        "highlight_timestamp": {
                            "timestamp1": None,
                            "timestamp2": None, 
                            "timestamp3": None, 
                            "timestamp4": None, 
                            "timestamp5": None, 
                            "timestamp6": None, 
                        }
                    },
                    "opinion": None,
                    "opinion_reason": None,
                    "link": None,
                    "pros": [],
                    "cons": []
                    
                },
                "general_users": {
                    "total_reviews": None,
                    "positive_percentage": None,
                    "negative_percentage": None,
                    "positive_reviews": [],
                    "negative_reviews": [],
                    "user_comments": [
                        {
                            "user": None,
                            "comment": None
                        }
                    ]
                }
            },
            "purchase_info": {
                "stores": [
                    {
                        "site": None,
                        "option": None,
                        "price": None,
                        "purchase_link": None,
                        "rating": None
                    },
                    {
                        "site": None,
                        "option": None,
                        "price": None,
                        "purchase_link": None,
                        "rating": None
                    }
                ]
            }
        }
        return original_structure



    class TemplateGenerator:
        def __init__(self, template, path=""):
            """
            :param template: 템플릿 딕셔너리 (여기엔 dict, list, 도트표기 문자열, 단순 리터럴 문자열이 섞여 있음)
            :param path: 현재 노드의 경로 (재귀 호출용; 이제는 사용하지 않습니다)
            """
            self._template = template
            self._path = path  # 참고용으로 남겨두지만, 더 이상 접두사로 사용하지 않음
            self._data = {}
            self._build()

        def _build(self):
            for key, value in self._template.items():
                if isinstance(value, dict):
                    # 딕셔너리인 경우: 재귀적으로 TemplateGenerator로 처리
                    node =self.__class__(value, path="")  # 부모 경로 무시
                    setattr(self, key, node)
                    self._data[key] = node
                elif isinstance(value, list):
                    new_list = []
                    for item in value:
                        if isinstance(item, dict):
                            new_list.append(self.__class__(item, path=""))
                        elif isinstance(item, str):
                            if "." in item:
                                # 도트표기 문자열 처리: 부모 경로 무시하고, 문자열을 그대로 분리
                                parts = item.split(".")
                                new_list.append(self._create_nested(parts, None))
                            else:
                                # 단순 리터럴 문자열: 해당 문자열 자체를 속성명으로 하는 leaf 생성
                                leaf = type("Leaf", (), {})()
                                setattr(leaf, item, None)
                                new_list.append(leaf)
                        else:
                            new_list.append(item)
                    setattr(self, key, new_list)
                    self._data[key] = new_list
                elif isinstance(value, str):
                    if "." in value:
                        # 도트표기 문자열 처리: 부모 경로 무시하고, 문자열 그대로 분리
                        parts = value.split(".")
                        node = self._create_nested(parts, None)
                        setattr(self, key, node)
                        self._data[key] = node
                    else:
                        # 단순 리터럴 문자열: 그 자체를 속성명으로 하는 leaf 생성
                        node = type("Leaf", (), {})()
                        setattr(node, value, None)
                        # 여기서는 템플릿의 key 대신 리터럴 자체를 속성명으로 사용
                        setattr(self, value, node)
                        self._data[value] = node
                else:
                    setattr(self, key, value)
                    self._data[key] = value

        def _create_nested(self, parts, final_value):
            """
            parts: 도트로 분리된 리스트 (예: ["value"] 또는 ["subkey", "value"])
            final_value: 최종 리프 노드에 들어갈 기본 값 (None)
            입력받은 parts를 그대로 사용해 중첩 객체(leaf, node)를 생성합니다.
            """
            if not parts:
                return final_value
            head = parts[0]
            if len(parts) == 1:
                node = type("Leaf", (), {})()
                setattr(node, head, final_value)
                return node
            else:
                child = self._create_nested(parts[1:], final_value)
                node = type("Node", (), {})()
                setattr(node, head, child)
                return node

        def dict(self):
            """
            객체 내부의 데이터를 재귀적으로 딕셔너리로 변환하여 반환합니다.
            """
            result = {}
            for key, value in self._data.items():
                attr = getattr(self, key)
                if isinstance(attr, self.__class__):
                    result[key] = attr.dict()
                elif isinstance(attr, list):
                    new_list = []
                    for item in attr:
                        if isinstance(item, self.__class__):
                            new_list.append(item.dict())
                        elif self._is_object_with_attrs(item):
                            new_list.append(self._object_to_dict(item))
                        else:
                            new_list.append(item)
                    result[key] = new_list
                elif self._is_object_with_attrs(attr):
                    result[key] = self._object_to_dict(attr)
                else:
                    result[key] = attr
            return result

        def _is_object_with_attrs(self, obj):
            return hasattr(obj, "__dict__") and not isinstance(obj, type)

        def _object_to_dict(self, obj):
            d = {}
            for attr_name, attr_val in obj.__dict__.items():
                if self._is_object_with_attrs(attr_val):
                    d[attr_name] = self._object_to_dict(attr_val)
                else:
                    d[attr_name] = attr_val
            return d

# ================= 사용 예시 =================


# 템플릿 인스턴스 생성 (미리 정의된 original_structure 사용)

# 직접 딕셔너리 키를 사용하여 값을 채우는 예시



class Product_recommendation():
    def __init__(self):
        self.name = None
        self.category = None
        self.main_reason = None
        self.sub_reason = None
        self.good_person = []
        self.bad_person = []
    def show(self):
        print("name,category,main_reason,sub_reason,good_person,bad_person}")
        return "name,category,main_reason,sub_reason,good_person,bad_person}"
    def set_value(self,result_dict):
        result_dict["product"]["recommendation"]["main_reason"]=self.main_reason
        result_dict["product"]["recommendation"]["sub_reason"]=self.sub_reason
        result_dict["product"]["recommendation"]["good_person"]=self.good_person
        result_dict["product"]["recommendation"]["bad_person"]=self.bad_person
        result_dict["product"]["name"]=self.name
        result_dict["product"]["category"]=self.category
        return result_dict

class Secifications_Display():
    def __init__(self):
        self.size = None
        self.resolution = None
        self.refresh_rate = None
        self.description = None
        
    def show(self):
        print("size,resolution,refresh_rate,description")
        return "size,resolution,refresh_rate,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["display"]["size"]=self.size
        result_dict["product"]["specifications"]["display"]["resolution"]=self.resolution
        result_dict["product"]["specifications"]["display"]["refresh_rate"]=self.refresh_rate
        result_dict["product"]["specifications"]["display"]["description"]=self.description
        return result_dict
class Secifications_Processor():
    def __init__(self):
        self.model = None
        self.equivalent = None
        self.description = None
    def show(self):
        print("model,equivalent,description")
        return "model,equivalent,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["processor"]["model"]=self.model
        result_dict["product"]["specifications"]["processor"]["equivalent"]=self.equivalent
        result_dict["product"]["specifications"]["processor"]["description"]=self.description
        return result_dict
class Secifications_Storage():
    def __init__(self):
        self.options = []
        self.expandable = None
        self.description = None
    def show(self):
        print("options,expandable,description")
        return "options,expandable,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["storage"]["options"]=self.options
        result_dict["product"]["specifications"]["storage"]["expandable"]=self.expandable
        result_dict["product"]["specifications"]["storage"]["description"]=self.description
        return result_dict
class Secifications_Battery():
    def __init__(self):
        self.capacity = None
        self.description = None
    def show(self):
        print("capacity,description")
        return "capacity,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["battery"]["capacity"]=self.capacity
        result_dict["product"]["specifications"]["battery"]["description"]=self.description
        return result_dict
class Secifications_Design():
    def __init__(self):
        self.features = []
        self.description = None
    def show(self):
        print("features,description")
        return "features,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["design"]["features"]=self.features
        result_dict["product"]["specifications"]["design"]["description"]=self.description
        return result_dict
class Secifications_Color_Options():
    def __init__(self):
        self.color_options = []
    def show(self):
        print("color_options")
        return "color_options"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["color_options"]=self.color_options
        return result_dict
class Secifications_Pencil_Support():
    def __init__(self):
        self.supported = None
        self.charging = None
        self.description = None
    def show(self):
        print("supported,charging,description")
        return "supported,charging,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["pencil_support"]["supported"]=self.supported
        result_dict["product"]["specifications"]["pencil_support"]["charging"]=self.charging
        result_dict["product"]["specifications"]["pencil_support"]["description"]=self.description
        return result_dict
class Secifications_Charging_Port():
    def __init__(self):
        self.type = None
        self.limitation = None
        self.description = None
    def show(self):
        print("type,limitation,description")
        return "type,limitation,description"
    def set_value(self,result_dict):
        result_dict["product"]["specifications"]["charging_port"]["type"]=self.type
        result_dict["product"]["specifications"]["charging_port"]["limitation"]=self.limitation
        result_dict["product"]["specifications"]["charging_port"]["description"]=self.description
        return result_dict
class Reviews_Youtuber():
    def __init__(self):
        self.name = None
        self.subscribers = None
        self.title = None
        self.views = None
        self.time_since_upload=None
        self.timestamp1= None
        self.timestamp2= None 
        self.timestamp3= None 
        self.timestamp4= None 
        self.timestamp5= None 
        self.timestamp6= None 
        self.timestamp1_description= None 
        self.timestamp2_description= None 
        self.timestamp3_description= None 
        self.timestamp4_description= None 
        self.timestamp5_description= None 
        self.timestamp6_description= None    
        self.opinion = None
        self.opinion_reason = None
        self.pros = []
        self.cons = []
        self.link = None
    def show(self):
        print("name,subscribers,title,views,time_since_upload,timestamp1,timestamp2,timestamp3,timestamp4,timestamp5,timestamp6,opinion,opinion_reason,pros,cons,link")
        return "name,subscribers,title,views,time_since_upload,timestamp1,timestamp2,timestamp3,timestamp4,timestamp5,timestamp6,opinion,opinion_reason,pros,cons,link"
    def set_value(self,result_dict):
        result_dict["reviews"]["youtuber"]["name"]=self.name
        result_dict["reviews"]["youtuber"]["subscribers"]=self.subscribers
        result_dict["reviews"]["youtuber"]["review_video"]["title"]=self.title
        result_dict["reviews"]["youtuber"]["review_video"]["views"]=self.views
        result_dict["reviews"]["youtuber"]["review_video"]["time_since_upload"]=self.time_since_upload
        if not self.timestamp1:
            self.timestamp1=""
        if not self.timestamp2:
            self.timestamp2=""
        if not self.timestamp3:
            self.timestamp3=""
        if not self.timestamp4:
            self.timestamp4=""
        if not self.timestamp5:
            self.timestamp5=""
        if not self.timestamp6:
            self.timestamp6=""
        if not self.timestamp1_description:
            self.timestamp1_description=""
        if not self.timestamp2_description:
            self.timestamp2_description=""
        if not self.timestamp3_description:
            self.timestamp3_description=""
        if not self.timestamp4_description:
            self.timestamp4_description=""
        if not self.timestamp5_description:
            self.timestamp5_description=""
        if not self.timestamp6_description:
            self.timestamp6_description=""
        
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp1"]=self.timestamp1 + " : "+ self.timestamp1_description
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp2"]=self.timestamp2 + " : "+ self.timestamp2_description
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp3"]=self.timestamp3 + " : "+ self.timestamp3_description
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp4"]=self.timestamp4 + " : "+ self.timestamp4_description
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp5"]=self.timestamp5 + " : "+ self.timestamp5_description
        result_dict["reviews"]["youtuber"]["review_video"]["highlight_timestamp"]["timestamp6"]=self.timestamp6 + " : "+ self.timestamp6_description
        result_dict["reviews"]["youtuber"]["opinion"]=self.opinion
        result_dict["reviews"]["youtuber"]["opinion_reason"]=self.opinion_reason
        result_dict["reviews"]["youtuber"]["pros"]=self.pros
        result_dict["reviews"]["youtuber"]["cons"]=self.cons
        result_dict["reviews"]["youtuber"]["link"]=self.link
        return result_dict
    
    def process_dict(self, result_dict, mode="set"):
        """
        mode="set": 플래트 딕셔너리 (키가 "youtuber.attribute" 형태)로 인스턴스의 속성을 업데이트합니다.
        mode="get": 인스턴스의 속성값을 바탕으로 중첩된 딕셔너리 구조를 반환합니다.
        """
        if mode == "set":
            prefix = "youtuber."
            for key, value in result_dict.items():
                if key.startswith(prefix):
                    attr_name = key[len(prefix):].replace('.','')
                else:
                    attr_name = key
                if hasattr(self, attr_name):
                    setattr(self, attr_name, value)
                else:
                    print(f"Warning: '{attr_name}' 속성이 클래스에 없습니다.")
            # 업데이트 후, self를 반환할 수도 있음.
            return self
        elif mode == "get":
            # 중첩된 딕셔너리 구조로 결과를 생성
            output = {
                "reviews": {
                    "youtuber": {
                        "name": self.name,
                        "subscribers": self.subscribers,
                        "review_video": {
                            "title": self.title,
                            "views": self.views,
                            "time_since_upload": self.time_since_upload,
                            "highlight_timestamp": {
                                "timestamp1": f"{self.timestamp1} : {self.timestamp1_description}",
                                "timestamp2": f"{self.timestamp2} : {self.timestamp2_description}",
                                "timestamp3": f"{self.timestamp3} : {self.timestamp3_description}",
                                "timestamp4": f"{self.timestamp4} : {self.timestamp4_description}",
                                "timestamp5": f"{self.timestamp5} : {self.timestamp5_description}",
                                "timestamp6": f"{self.timestamp6} : {self.timestamp6_description}"
                            }
                        },
                        "opinion": self.opinion,
                        "opinion_reason": self.opinion_reason,
                        "pros": self.pros,
                        "cons": self.cons,
                        "link": self.link
                    }
                }
            }
            return output
        else:
            raise ValueError("mode 인자는 'set' 또는 'get'이어야 합니다.")

 
    
    
    
    
    
class Reviews_General_Users():
    def __init__(self):
        self.total_reviews = None
        self.positive_percentage = None
        self.negative_percentage = None
        self.positive_reviews = []
        self.negative_reviews = []
        self.user_comments = []
    def show(self):
        print("total_reviews,positive_percentage,negative_percentage,positive_reviews,negative_reviews,user_comments")
        return "total_reviews,positive_percentage,negative_percentage,positive_reviews,negative_reviews,user_comments"
    def set_value(self,result_dict):
        result_dict["reviews"]["general_users"]["total_reviews"]=self.total_reviews
        result_dict["reviews"]["general_users"]["positive_percentage"]=self.positive_percentage
        result_dict["reviews"]["general_users"]["negative_percentage"]=self.negative_percentage
        result_dict["reviews"]["general_users"]["positive_reviews"]=self.positive_reviews
        result_dict["reviews"]["general_users"]["negative_reviews"]=self.negative_reviews
        result_dict["reviews"]["general_users"]["user_comments"]=self.user_comments
        return result_dict
    def process_dict(self, result_dict, mode="set"):
        """
        mode="set": 플래트 딕셔너리 (키가 "reviews.attribute" 형태)로 인스턴스의 속성을 업데이트합니다.
        mode="get": 인스턴스의 속성값을 바탕으로 중첩된 딕셔너리 구조를 반환합니다.
        """
        if mode == "set":
            prefix = "general_users"
            for key, value in result_dict.items():
                if key.startswith(prefix):
                    attr_name = key[len(prefix):].replace('.','')
                else:
                    attr_name = key
                if hasattr(self, attr_name):
                    setattr(self, attr_name, value)
                else:
                    print(f"Warning: '{attr_name}' 속성이 클래스에 없습니다.")
            # 업데이트 후, self를 반환할 수도 있음.
            return self
        elif mode == "get":
            # 중첩된 딕셔너리 구조로 결과를 생성
            output = {
                "reviews": {
                    "general_users": {  "total_reviews": self.total_reviews,
                                        "positive_percentage": self.positive_percentage,
                                        "negative_percentage": self.negative_percentage,
                                        "positive_reviews": self.positive_reviews,
                                        "negative_reviews": self.negative_reviews,
                                        "user_comments": self.user_comments
                                        }
                                        
                            }
            }
            return output
        else:
            raise ValueError("mode 인자는 'set' 또는 'get'이어야 합니다.")


class Product():
    def __init__(self):
        self.recommendation = Product_recommendation()
        self.display = Secifications_Display()
        self.processor = Secifications_Processor()
        self.storage = Secifications_Storage()
        self.battery = Secifications_Battery()
        self.design = Secifications_Design()
        self.color_options = Secifications_Color_Options()
        self.pencil_support = Secifications_Pencil_Support()
        self.charging_port = Secifications_Charging_Port()
        
    def show(self):
        print("recommendation,specifications_display,specifications_processor,specifications_storage,specifications_battery,specifications_design,specifications_color_options,specifications_pencil_support,specifications_charging_port")
        return "recommendation,specifications_display,specifications_processor,specifications_storage,specifications_battery,specifications_design,specifications_color_options,specifications_pencil_support,specifications_charging_port"
    def set_value(self,result_dict):
        self.recommendation.set_value(result_dict)
        self.display.set_value(result_dict)
        self.processor.set_value(result_dict)
        self.storage.set_value(result_dict)
        self.battery.set_value(result_dict)
        self.design.set_value(result_dict)
        self.color_options.set_value(result_dict)
        self.pencil_support.set_value(result_dict)
        self.charging_port.set_value(result_dict)
        return result_dict
    def process_dict(self, flat_dict):
        """
        flat_dict의 키는 "키접두어.속성" 형태입니다.
        예: "specifications_display.size" 또는 "recommendation.name"
        
        Product 클래스 내부에는 다음 멤버가 있습니다:
            - recommendation
            - display
            - processor
            - storage
            - battery
            - design
            - color_options
            - pencil_support
            - charging_port
        
        만약 flat_dict의 키 접두어가 실제 멤버명과 다르다면, 아래 mapping을 통해 변환합니다.
        """
        mapping = {
            "recommendation": "recommendation",
            "specifications_display": "display",
            "display": "display",
            "specifications_processor": "processor",
            "processor": "processor",
            "specifications_storage": "storage",
            "storage": "storage",
            "specifications_battery": "battery",
            "battery": "battery",
            "specifications_design": "design",
            "design": "design",
            "specifications_color_options": "color_options",
            "color_options": "color_options",
            "specifications_pencil_support": "pencil_support",
            "pencil_support": "pencil_support",
            "specifications_charging_port": "charging_port",
            "charging_port": "charging_port"
        }
        
        for key, value in flat_dict.items():
            parts = key.split(".", 1)
            if len(parts) != 2:
                print(f"Warning: Key '{key}' does not follow the 'subobject.attribute' format.")
                continue
            sub_key, attr_name = parts
            # 변환 매핑을 통해 실제 멤버 이름을 얻습니다.
            if sub_key in mapping:
                obj_attr = mapping[sub_key]
            else:
                obj_attr = sub_key  # 매핑이 없으면 그대로 사용
            if hasattr(self, obj_attr):
                sub_obj = getattr(self, obj_attr)
                if hasattr(sub_obj, attr_name):
                    setattr(sub_obj, attr_name, value)
                else:
                    print(f"Warning: '{obj_attr}' object has no attribute '{attr_name}'.")
            else:
                print(f"Warning: Product has no sub-object named '{obj_attr}'.")
        return self

class Reviews():
    def __init__(self):
        self.youtuber = Reviews_Youtuber()
        self.general_users = Reviews_General_Users()
    def show(self):
        print("youtuber,general_users")
        return "youtuber,general_users"
    def set_value(self,result_dict):
        self.youtuber.set_value(result_dict)
        self.general_users.set_value(result_dict)
        return result_dict
class Purchase_Info_Stores():
    def __init__(self):
        self.site = None
        self.option = None
        self.price = None
        self.purchase_link = None
        self.rating = None
    def show(self):
        print("site,option,price,purchase_link,rating")
        return "site,option,price,purchase_link,rating"
    def set_value(self,result_dict):
        result_dict["purchase_info"]["stores"]={"site":self.site,
                                            "option" : self.option,
                                            "price":self.price,
                                            "purchase_link":self.purchase_link,
                                            "rating":self.rating}
        return result_dict
    def process_dict(self, flat_dict):
        self.price=flat_dict["price"]
        self.site=flat_dict["site"]
        self.option=flat_dict["option"]
        self.purchase_link=flat_dict["purchase_link"]
        self.rating=flat_dict["rating"]
        
            
        
class Youtuber:
    def __init__(self,input):
        self.name = None
        self.subscribers = None
        self.title = None
        self.views = None
        self.time_since_upload = None
        self.timestamp1 = None
        self.timestamp2 = None
        self.timestamp3 = None
        self.timestamp4 = None
        self.timestamp5 = None
        self.timestamp6 = None
        self.timestamp1_description = None
        self.timestamp2_description = None
        self.timestamp3_description = None
        self.timestamp4_description = None
        self.timestamp5_description = None
        self.timestamp6_description = None
        self.opinion = None
        self.opinion_reason = None
        self.pros = None
        self.cons = None
        self.link = None

    def set_value(self, result_dict):
        # result_dict 의 키는 "youtuber.attribute" 형태입니다.
        prefix = "youtuber."
        for key, value in result_dict.items():
            # 접두사가 있다면 제거하여 실제 속성 이름을 얻습니다.
            if key.startswith(prefix):
                attr_name = key[len(prefix):].replace('.','')
            else:
                attr_name = key
            # 해당 속성이 클래스에 존재하면 할당
            if hasattr(self, attr_name):
                setattr(self, attr_name, value)
            else:
                print(f"Warning: '{attr_name}' 속성이 클래스에 없습니다.")
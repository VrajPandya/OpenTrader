## Note: this method mutates the "to_obj"
def dict_to_obj(from_dict, to_obj):
    for key in from_dict:
        setattr(to_obj, key, from_dict[key])
        
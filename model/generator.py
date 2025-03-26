

class Generator:
    def __init__(self, dataset, when, what):
        self.dataset = dataset
        self.when = when
        self.what = what

    def prepare_run(self, full_loaders, user_filter, initial_time=None, final_time=None, interval=60, time_loader=None):
        self.users = [uid for uid in self.dataset.user_pool.uids if user_filter(self.dataset.entity_factory("user", uid, full_loaders['user']))]

        if initial_time == None:
            self.initial_time = min([root.fetch_submission_object(time_loader).get_time() for root in self.dataset.sf.roots])
        else:
            self.initial_time = initial_time

        if final_time == None:
            self.final_time = max([root.dfs(lambda s: max(s['sub_obj'].get_time(), s['desc_result']), loader=time_loader, reduce_kids_acc=0, reduce_kids_f=lambda acc, i: max(acc, i)) for root in self.sf.roots])
        else:
            self.final_time = final_time
        #activate all before time

        #remove some?

        for t in range(initial_time, final_time, interval):
            self.generate()
            


    def generate(self):
        for user in self.users:
            user_object = user.fetch_submission_object(full_loaders['user'])
            for root in self.dataset.sf.roots:
                root_object = root.fetch_submission_object(full_loaders['root'])
                
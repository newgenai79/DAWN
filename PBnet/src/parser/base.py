from argparse import ArgumentParser  # noqa


def add_misc_options(parser):
    group = parser.add_argument_group('Miscellaneous options')
    group.add_argument("--expname", default="exps", help="general directory to this experiments, use it if you don't provide folder name")
    group.add_argument("--folder", default="exps/default_path", help="directory name to save models")
    

def add_cuda_options(parser):
    group = parser.add_argument_group('Cuda options')
    group.add_argument("--cuda", dest='cuda', action='store_true', help="if we want to try to use gpu")
    group.add_argument('--cpu', dest='cuda', action='store_false', help="if we want to use cpu")
    group.set_defaults(cuda=True)
    
    group.add_argument("--gpu", default='0', help="choose gpu device.")

    
def adding_cuda(parameters):
    import torch
    if (parameters["cuda"] or parameters["gpu"])  and torch.cuda.is_available():
        parameters["device"] = torch.device("cuda")
    else:
        parameters["device"] = torch.device("cpu")
        
    

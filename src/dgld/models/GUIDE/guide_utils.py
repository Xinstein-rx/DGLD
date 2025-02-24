import torch 
import dgl 
import numpy as np
import os,sys
current_file_name = __file__
current_dir=os.path.dirname(os.path.dirname(os.path.abspath(current_file_name)))
if current_dir not in sys.path:
    sys.path.append(current_dir)
from utils.common_params import IN_FEATURE_MAP



def set_subargs(parser):
    parser.add_argument('--attrb_hid', type=int, default=64,
                    help='dimension of hidden embedding for attribute encoder (default: 64)')
    parser.add_argument('--struct_hid', type=int, default=32,
                    help='dimension of hidden embedding for structure encoder (default: 8)')
    parser.add_argument('--num_epoch', type=int, help='Training epoch')
    parser.add_argument('--lr', type=float,default = 0.01, help='learning rate')
    parser.add_argument('--dropout', type=float,
                        default=0.5, help='Dropout rate')
    parser.add_argument('--alpha', type=float, default=0.99,
                        help='balance parameter')
    parser.add_argument('--struct_dim', type=int, default=6,
                        help='struct feature dim')
    parser.add_argument('--num_layers', type=int, default=4,
                        help='the number of layers')
    parser.add_argument('--batch_size', type=int, default=0,help='batch_size, 0 for all data ')

def get_subargs(args):
    if args.num_epoch is None:
        if args.dataset in ['Cora', 'Citeseer']:
            args.num_epoch = 100
        elif args.dataset in [ 'Flickr', 'ACM']:
            args.num_epoch = 50
        else:
            args.num_epoch = 10
    if args.dataset == 'Cora':
        args.alpha = 0.9987
        args.lr = 0.001
    if args.dataset == 'Citeseer':
        args.alpha = 0.9997
    if args.dataset == 'Pubmed':
        args.alpha = 0.9996
        args.lr = 0.001
        args.attrb_hid = 256
        args.num_epoch = 400
    if args.dataset == 'BlogCatalog':
        args.alpha = 1
        args.lr = 0.01
        args.num_epoch = 100
        args.attrb_hid = 128
        args.batch_size = 2048
        args.dropout=0.3
    if args.dataset == 'Flickr':
        args.alpha = 1
    if args.dataset == 'ACM':
        args.alpha = 0.81
        args.lr = 0.001
        args.attrb_hid = 256
        args.struct_hid = 64
        args.batch_size = 2048
    if args.dataset == 'ogbn-arxiv':
        args.alpha = 0.999
        args.lr = 0.001
        args.attrb_hid = 64
        args.struct_hid = 16
        args.batch_size = 2048
    
    final_args_dict = {
        "dataset": args.dataset,
        "seed": args.seed,
        "model":{
            "attrb_dim": IN_FEATURE_MAP[args.dataset],
            "struct_dim": args.struct_dim,
            "num_layers": args.num_layers,
            "attrb_hid": args.attrb_hid,
            "struct_hid": args.struct_hid,
            "dropout": args.dropout,
        },
        "fit":{
            "num_epoch":args.num_epoch,
            "batch_size":args.batch_size,
            "lr":args.lr,
            "alpha":args.alpha,
            "device":args.device
        },
        "predict":{
            "alpha":args.alpha,
            "batch_size":args.batch_size,
            "device":args.device
        }
    }
    return final_args_dict,args

def cal_motifs(nx_g,x,idx):
    """
    count the number of motifs 

    Parameters
    ----------
    nx_g : networkx.Graph
        the graph
    x: int
        the node id you want count
    idx: int
        the motifs id you want count

    Returns
    -------
    the number of motifs
    """
    sum = 0 
    if idx == 0:
        adj_x = list(nx_g[x].keys())
        size = len(adj_x)
        for i in range(size):
            y = adj_x[i]
            adj_y = list(nx_g[y].keys())
            res = set(adj_x) & set(adj_y)
            sum += len(res)
        return sum // 2
    if idx == 1:
        adj_x = list(nx_g[x].keys())
        for i in range(len(adj_x)):
            y = adj_x[i]
            adj_y = set(nx_g[y].keys())
            res = adj_y - set(adj_x)
            sum += len(res) - 1

            res = set(adj_x[i+1:]) - adj_y
            sum += len(res)
        return sum
    if idx == 2:
        size = len(nx_g[x])
        adj_x = list(nx_g[x].keys())
        for i in range(size):
            y = adj_x[i]
            adj_y = set(nx_g[y].keys())
            for j in range(i+1,size):
                z = adj_x[j]
                if z not in adj_y:
                    continue
                adj_z = set(nx_g[z].keys())
                a_list =  adj_y & set(adj_x[j+1:]) & adj_z
                sum += len(a_list)
        return sum 
    if idx == 3:
        size = len(nx_g[x])
        adj_x = list(nx_g[x].keys())
        for i in range(size):
            y = adj_x[i]
            adj_y = set(nx_g[y].keys())

            rx = set(adj_x[i+1:])
            z_set = rx - adj_y
            for z in z_set:
                adj_z = set(nx_g[z].keys())
                res = adj_z & adj_y & set(adj_x)
                sum += len(res)
            z_set = rx & adj_y
            for z in z_set:
                adj_z = set(nx_g[z].keys())
                res = adj_z & adj_y - set(adj_x)
                sum += len(res) - 1

        return sum 
    if idx == 4:
        size = len(nx_g[x])
        adj_x = list(nx_g[x].keys())
        for i in range(size):
            y = adj_x[i]
            adj_y = set(nx_g[y].keys())
            z_list = set(adj_x[i+1:]) - adj_y
            for z in z_list:
                adj_z = set(nx_g[z].keys())
                res = adj_z & adj_y - set(adj_x) 
                sum += len(res) - 1
        return sum 
def get_struct_feat(graph:dgl.DGLGraph):
    """
    Generate the struct feature.Use the number of the motifs to express.
    
    Parameters
    ----------
    graph : DGL.Graph
        input graph

    Returns
    -------
    the struct feature 
    """
    print("generate struct feature")
    new_g = graph.to_simple()
    new_g = new_g.remove_self_loop()
    nx_g = new_g.to_networkx().to_undirected()
    node_num = new_g.num_nodes()
    struct_feat = np.zeros((node_num,6))
    for i in range(node_num):
        struct_feat[i][5] = len(nx_g[i])
        for  idx in range(5):
            struct_feat[i][idx] = cal_motifs(nx_g,i,idx)
    return torch.tensor(struct_feat,dtype=torch.float32)
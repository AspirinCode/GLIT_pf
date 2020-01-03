import numpy as np
import pandas as pd
import pickle
import random

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.autograd import gradcheck

from torch_geometric.data import Data, DataListLoader

import networkx as nx
from scipy import sparse

from sklearn import preprocessing
from sklearn.metrics import f1_score, roc_auc_score, average_precision_score, accuracy_score

from model import *
from utils2 import *

import argparse

import os

from trainer import TrainAndTest, ValidAndTest

#   #   #   #   #   #   
seed = 44
torch.manual_seed(seed)
torch.cuda.manual_seed(seed)
torch.cuda.manual_seed_all(seed)
np.random.seed(seed)
random.seed(seed)

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False
#   #   #   #   #   #   

def Get_Models(ppi_adj, g2v_embedding, args, device):

    if args.model == 'GEX_PPI_GAT_cat4_MLP':
        return GEX_PPI_GAT_cat4_MLP(ppi_adj, g2v_embedding, args).to(device)

    elif args.model == 'GEX_PPI_GAT_cat7_MLP':
        return GEX_PPI_GAT_cat7_MLP(ppi_adj, g2v_embedding, args).to(device)

    elif args.model == 'GEX_PPI_GCN_cat4_MLP':
        return GEX_PPI_GCN_cat4_MLP(ppi_adj, g2v_embedding, args).to(device)
    
    elif args.model == 'GEX_PPI_SAGE_cat4_MLP':
        return GEX_PPI_SAGE_cat4_MLP(ppi_adj, g2v_embedding, args).to(device)

    elif args.model == 'GEX_PPI_HIGHER_cat4_MLP':
        return GEX_PPI_HIGHER_cat4_MLP(ppi_adj, g2v_embedding, args).to(device)

def main(args):

    os.environ["CUDA_VISIBLE_DEVICES"] = args.device[-1]


    #   Get Input List
    """
    x[0] = ecfp
    x[1] = l1000 gex
    x[2] = dosage
    x[3] = duration
    x[4] = label
    x[5] = pert_iname
    x[6] = cell_id
    x[7] = smiles string
    """
    if args.gex_feat == 'l1000':
        with open('data/labeled_list_woAmbi_92742_70138.pkl', 'rb') as f:
            input_list = pickle.load(f)

    args.num_genes = len(input_list[0][1])


    #   For 2 class analysis
    if args.num_classes == 2:
        for i, x in enumerate(input_list):
            if input_list[i][4] == 2:
                input_list[i][4] = 1

    drug_label = pd.read_csv('data/drug_label_92742_70138.tsv',
                                    delimiter = '\t',
                                    index_col = 0) 


    gene_info = get_gene_info(args)
    #   index : gene num, 'pr_gene_sympol' : gene symbol


    random.shuffle(input_list)

    from sklearn.utils import shuffle
    drug_label = shuffle(drug_label, random_state = args.seed).copy()
    

#  use ecfp feature
    # for i, x in enumerate(input_list):
    #     input_list[i].append(get_ecfp_fingerprints(x[7], args))

    if 'PPI' in args.model:
        gene2vecdict, gene_info, ppi_adj, ppi_nx, g2v_embedding, get_gex_idxs, args = get_ppi_features(gene_info, args)


    #   Scores over 5 random samples
    valid_avg_scores = []
    valid_drug_scores = []
    avg_scores = []
    drug_scores = []



    for n_sample in range(5):

        #   dataset separation by drugs
        train_loader, valid_loader, test_loader =  Get_DataLoader(drug_label, input_list, args)

        device = torch.device(args.device)

        #   Choose Model

        model = Get_Models(ppi_adj, g2v_embedding, args, device)

        def init_normal(m):
            if type(m) == nn.Linear:
                nn.init.xavier_normal_(m.weight)

        model.apply(init_normal)
        print(model.parameters)
        

        loss_fn = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(model.parameters(), 
                                    lr = args.learning_rate,
                                    weight_decay = args.weight_decay)

        scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, 
                                                        gamma = 0.95)


#        model_path = 'models/'+str(args.model)+str(args.num_gcn_hops)+'_'+str(args.drug_feat)+'_'+str(args.gex_feat)+'_'+str(args.learning_rate)+'_'+str(args.weight_decay)+'_'+str(args.n_epochs)+'_'+str(args.attn_dim)+'_'+str(args.loss_alpha)+'_'+str(args.g2v_pretrained)+'_'+str(args.seed)+'_ver'+str(args.dataset_ver) 
        model_path = 'models/'+str(args.model)+str(args.num_gcn_hops)+'_'+str(args.drug_feat)+'_'+str(args.gex_feat)+'_'+str(args.learning_rate)+'_'+str(args.weight_decay)+'_'+str(args.n_epochs)+'_'+str(args.g2v_pretrained)+'_'+str(args.seed)+'_ver'+str(args.dataset_ver) 
            

        if args.eval == True:
            model.load_state_dict(torch.load(model_path, map_location = args.device))
            valid_pred, valid_proba, valid_label, valid_drug_names,\
                    test_pred, test_proba, test_label, test_drug_names = ValidAndTest(
                        valid_loader, test_loader, model, optimizer, 
                        loss_fn, scheduler, device, ppi_adj, get_gex_idxs, args)
            

        else:
            valid_pred, valid_proba, valid_label, valid_drug_names,\
                    test_pred, test_proba, test_label, test_drug_names, model = TrainAndTest(
                        train_loader, valid_loader, test_loader, model, optimizer, 
                        loss_fn, scheduler, device, ppi_adj, get_gex_idxs, n_sample, args)


        valid_drug_labels_avg, valid_drug_preds_avg, valid_drug_probas_avg, \
                valid_drug_names_avg = Get_Drugwise_Preds(
                        valid_label, valid_pred, valid_proba, valid_drug_names)


        test_drug_labels_avg, test_drug_preds_avg, test_drug_probas_avg, \
                test_drug_names_avg = Get_Drugwise_Preds(
                        test_label, test_pred, test_proba, test_drug_names)
            
        #   save model state_dict
        if (args.save_model == True) & (args.eval == False):
            torch.save(model.state_dict(), model_path)

        with open(model_path+'_preds.pkl', 'wb') as f:
            pickle.dump([test_drug_preds_avg, test_drug_probas_avg, 
                    test_drug_labels_avg, test_drug_names_avg], f)

        valid_avg_scores.append(Return_Scores(valid_label, valid_pred, valid_proba))
        valid_drug_scores.append(Return_Scores(valid_drug_labels_avg, valid_drug_preds_avg, valid_drug_probas_avg))
        avg_scores.append(Return_Scores(test_label, test_pred, test_proba))
        drug_score = Return_Scores(test_drug_labels_avg, test_drug_preds_avg, test_drug_probas_avg)
        drug_scores.append(Return_Scores(test_drug_labels_avg, test_drug_preds_avg, test_drug_probas_avg))

        args.seed += 1
        #   #   #   #   #   iter ends

    valid_avg_mean = np.mean(valid_avg_scores, axis = 0)
    valid_avg_std = np.std(valid_avg_scores, axis = 0)
    valid_drug_mean = np.mean(valid_drug_scores, axis = 0)
    valid_drug_std = np.std(valid_drug_scores, axis = 0)

    avg_mean = np.mean(avg_scores, axis = 0)
    avg_std = np.std(avg_scores, axis = 0)
    drug_mean = np.mean(drug_scores, axis = 0)
    drug_std = np.std(drug_scores, axis = 0)

    print("Total valid Avg Scores")
    print(valid_avg_mean)
    print("Total valid Avg Std")
    print(valid_avg_std)
    print("Total valid Drug Scores")
    print(valid_drug_mean)
    print("Total valid Drug Std")
    print(valid_drug_std)

    print("Total Avg Scores")
    print(avg_mean)
    print("Total Avg Std")
    print(avg_std)
    print("Total Drug Scores")
    print(drug_mean)
    print("Total Drug Std")
    print(drug_std)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--model', type = str, default = 'GEX_PPI_GAT_cat4_MLP')


    parser.add_argument('--gex_feat', type = str, default = 'l1000')
    parser.add_argument('--drug_feat', type = str, default = 'ecfp')

    parser.add_argument('--batch_size', type = int, default = 32)
    parser.add_argument('--num_classes', type = int, default = 2)
    parser.add_argument('--n_epochs', type = int, default = 20)
    parser.add_argument('--seed', type = int, default = 44)
    parser.add_argument('--device', type = str, default = 'cuda')

    parser.add_argument('--ecfp_nBits', type = int, default = 2048)
    parser.add_argument('--ecfp_radius', type = int, default = 2)
    parser.add_argument('--num_genes', type = int, default = 978)

    parser.add_argument('--drug_embed_dim', type = int, default = 256)
    parser.add_argument('--gcn_hidden_dim1', type = int, default = 64)
    parser.add_argument('--num_gcn_hops', type = int, default = 3)
    parser.add_argument('--gat_num_heads', type = int, default = 4)
    parser.add_argument('--gene2vec_dim', type = int, default = 200)
    parser.add_argument('--learning_rate', type = float, default = 5e-4)
    parser.add_argument('--weight_decay', type = float, default = 1e-5)

    parser.add_argument('--g2v_pretrained', type = bool, default = True)
    parser.add_argument('--network_name', type = str, default = 'omnipath')
    parser.add_argument('--undir_graph', type = bool, default = False)

    parser.add_argument('--dataset_ver', type = int, default = 4)
    parser.add_argument('--save_model', type = bool, default = True)
    parser.add_argument('--eval', type = bool, default = False)



    args = parser.parse_args()


    if args.eval == True:
        args.save_model == False

    if not torch.cuda.is_available():
        args.device = 'cpu'

    main(args)
    print('Model : '+ args.model)
    print('num epochs : '+str(args.n_epochs))
    print('batch size : '+ str(args.batch_size))
    print('learning rate : ' + str(args.learning_rate))
    print('weight decay : ' + str(args.weight_decay))
    if 'PPI' in args.model:
        print('gcn hidden dim : '+ str(args.gcn_hidden_dim1))
        print('network name : ' + str(args.network_name))
        print('GCN/GAT num hops: '+str(args.num_gcn_hops))
        print('gat num heads : ' + str(args.gat_num_heads))
    
    print('drug embed dim : '+str(args.drug_embed_dim))

    print('use g2v pretrained : '+str(args.g2v_pretrained))
    print('dataset ver : '+str(args.dataset_ver))

    print('=    '*8)
    


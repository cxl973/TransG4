import tensorflow as tf
from tensorflow.keras.models import load_model
import numpy as np

from flask import Flask, jsonify, make_response, request
from flask_cors import CORS

def pearson(true, pred):
    x = tf.convert_to_tensor(true)
    y = tf.cast(pred, x.dtype)
    xmean = tf.math.reduce_mean(x)
    ymean = tf.math.reduce_mean(y)

    xm = x - xmean
    ym = y - ymean

    xnorm = tf.norm(xm, ord=2)
    ynorm = tf.norm(ym, ord=2)

    r = tf.tensordot(xm / xnorm, ym / ynorm, axes=2)
    return r

def padding(mat, max_seq, val = 0, pad_side='around'):
    if pad_side == 'around':
        l1 = int(np.floor((max_seq - mat.shape[0]) / 2))
        l2 = int(max_seq - mat.shape[0] - l1)
        ze1 = np.ones((l1, mat.shape[1]), dtype='int')*val
        ze2 = np.ones((l2, mat.shape[1]), dtype='int')*val
        concate = np.concatenate((ze1, mat, ze2), axis=0)
    else:
        l = int(max_seq - mat.shape[0])
        ze = np.zeros((l, mat.shape[1]), dtype='int')
        if pad_side == 'right':
            concate = np.concatenate((mat, ze), axis=0)
        elif pad_side == 'left':
            concate = np.concatenate((ze, mat), axis=0)

    return concate


def oneHot(string, max_seq=None, pad_side='around', val_N=0):
    mat = np.zeros((len(string), 5), dtype=np.int8)
    trantab = str.maketrans('AaCcGgTtNYRWSKMBDHV', '0011223344444444444')
    data = list(string.translate(trantab))
    data_arr = np.array(data, dtype=np.int8)
    mat[range(data_arr.size), data_arr] = 1
    if val_N:
        mat = mat.astype(np.float16)
        ind = np.where(mat[:, -1] == 1)[0]
        mat[ind, :] = val_N
    mat = mat[:, :-1]

    if max_seq and len(string) < max_seq:
        mat = padding(mat, max_seq, val_N, pad_side)

    return mat

model = load_model('./Transformer_kernelsize_15', custom_objects={"pearson": pearson})  # load pre-trained model
print(model.summary())

sequence = 'CCCCCCCCCCCCCCC' * 14 + 'CCCCC'
onehot_seq = np.array(oneHot(sequence))[np.newaxis, :]

print(onehot_seq)

print(model.predict(onehot_seq))


app = Flask(__name__)
# 配置CORS，允许所有来源
CORS(app)

@app.route('/')
def index():
    return 'Welcome to the home page.'

@app.route('/api/data', methods=['GET'])
def api_data():
    # 这里返回一些示例数据
    sequence = request.args.get('sequence')
    origin_seq = sequence
    seq_len = len(sequence)
    if seq_len < 215:
        sequence = ['N' * (215 - seq_len) + sequence]
    else:
        sequence = [sequence[i : i + 215] for i in range(seq_len - 215 + 1)]
    sequence_list = np.array([oneHot(item) for item in sequence])
    print(sequence_list)
    print(sequence_list.shape)
    scores = model.predict(sequence_list)
    print(scores)

    data = []
    for idx in range(len(scores)):
        item = {}
        item['start'] = idx + 1
        item['end'] = idx + 215
        item['sequence'] = origin_seq[idx : idx + 215]
        item['mismatch'] = str(scores[idx][0])
        print(item)
        data.append(item)
    # data = [
    #         {
    #             'start': 1,
    #             'end': 215,
    #             'sequence': 'AGGCTGGCCTTCCAAA',
    #             'mismatch': "35.5",
    #         },
    #         {
    #             'start': 1,
    #             'end': 215,
    #             'sequence': 'AGGCTGGCCTTCCAAA',
    #             'mismatch': "36.5",
    #         }
    # ]
    response = make_response(jsonify(data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

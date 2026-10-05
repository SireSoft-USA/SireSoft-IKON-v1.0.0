#include <cuda_runtime.h>
#include <cmath>
#include <cstdio>
#include <cstring>

static char g_last_error[1024] = "";

static int fail(cudaError_t error, const char* where) {
    if (error == cudaSuccess) return 0;
    std::snprintf(g_last_error, sizeof(g_last_error), "%s: %s", where, cudaGetErrorString(error));
    return (int)error;
}

static int check_launch(const char* where) {
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) return fail(e, where);
    e = cudaDeviceSynchronize();
    return fail(e, where);
}

extern "C" const char* sireikon_cuda_last_error() {
    return g_last_error;
}

extern "C" int sireikon_cuda_device_count(int* count) {
    cudaError_t e = cudaGetDeviceCount(count);
    return fail(e, "cudaGetDeviceCount");
}

extern "C" int sireikon_cuda_set_device(int index) {
    cudaError_t e = cudaSetDevice(index);
    return fail(e, "cudaSetDevice");
}

extern "C" int sireikon_cuda_synchronize() {
    return fail(cudaDeviceSynchronize(), "cudaDeviceSynchronize");
}

template <typename T>
static int alloc_copy_in(T** device, const T* host, size_t count, const char* where) {
    if (count == 0) { *device = nullptr; return 0; }
    cudaError_t e = cudaMalloc((void**)device, count * sizeof(T));
    if (e != cudaSuccess) return fail(e, where);
    e = cudaMemcpy(*device, host, count * sizeof(T), cudaMemcpyHostToDevice);
    if (e != cudaSuccess) {
        cudaFree(*device); *device = nullptr;
        return fail(e, where);
    }
    return 0;
}

template <typename T>
static int alloc_out(T** device, size_t count, const char* where) {
    if (count == 0) { *device = nullptr; return 0; }
    cudaError_t e = cudaMalloc((void**)device, count * sizeof(T));
    return fail(e, where);
}

template <typename T>
static int copy_out(T* host, const T* device, size_t count, const char* where) {
    if (count == 0) return 0;
    return fail(cudaMemcpy(host, device, count * sizeof(T), cudaMemcpyDeviceToHost), where);
}

static int product_host(const int* shape, int ndim) {
    int p = 1;
    for (int i = 0; i < ndim; ++i) p *= shape[i];
    return p;
}

__global__ void binary_broadcast_kernel(
    const float* left, const int* left_shape, int left_ndim,
    const float* right, const int* right_shape, int right_ndim,
    const int* out_shape, int out_ndim, int out_size, int mode,
    float* out
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= out_size) return;

    int remaining = idx;
    int left_index = 0;
    int right_index = 0;
    int left_stride = 1;
    int right_stride = 1;

    for (int axis = out_ndim - 1; axis >= 0; --axis) {
        int dim = out_shape[axis];
        int coord = (dim == 0) ? 0 : (remaining % dim);
        if (dim != 0) remaining /= dim;

        int la = axis - (out_ndim - left_ndim);
        if (la >= 0) {
            int ld = left_shape[la];
            int lc = (ld == 1) ? 0 : coord;
            left_index += lc * left_stride;
            left_stride *= ld;
        }

        int ra = axis - (out_ndim - right_ndim);
        if (ra >= 0) {
            int rd = right_shape[ra];
            int rc = (rd == 1) ? 0 : coord;
            right_index += rc * right_stride;
            right_stride *= rd;
        }
    }

    float a = left[left_index];
    float b = right[right_index];
    if (mode == 0) out[idx] = a + b;
    else if (mode == 1) out[idx] = a - b;
    else if (mode == 2) out[idx] = a * b;
    else out[idx] = a / b;
}

extern "C" int sireikon_cuda_binary_broadcast(
    const float* left, const int* left_shape, int left_ndim,
    const float* right, const int* right_shape, int right_ndim,
    const int* out_shape, int out_ndim, int mode, float* out
) {
    int left_size = product_host(left_shape, left_ndim);
    int right_size = product_host(right_shape, right_ndim);
    int out_size = product_host(out_shape, out_ndim);
    if (out_ndim == 0) out_size = 1;
    if (left_ndim == 0) left_size = 1;
    if (right_ndim == 0) right_size = 1;

    float *d_l=nullptr,*d_r=nullptr,*d_o=nullptr;
    int *d_ls=nullptr,*d_rs=nullptr,*d_os=nullptr;
    int rc=0;
    if ((rc=alloc_copy_in(&d_l,left,left_size,"binary left"))) goto done;
    if ((rc=alloc_copy_in(&d_r,right,right_size,"binary right"))) goto done;
    if (left_ndim && (rc=alloc_copy_in(&d_ls,left_shape,left_ndim,"binary left shape"))) goto done;
    if (right_ndim && (rc=alloc_copy_in(&d_rs,right_shape,right_ndim,"binary right shape"))) goto done;
    if (out_ndim && (rc=alloc_copy_in(&d_os,out_shape,out_ndim,"binary out shape"))) goto done;
    if ((rc=alloc_out(&d_o,out_size,"binary output"))) goto done;
    {
        int threads=256, blocks=(out_size+threads-1)/threads;
        binary_broadcast_kernel<<<blocks,threads>>>(d_l,d_ls,left_ndim,d_r,d_rs,right_ndim,d_os,out_ndim,out_size,mode,d_o);
        if ((rc=check_launch("binary kernel"))) goto done;
    }
    rc=copy_out(out,d_o,out_size,"binary result");
done:
    if(d_l)cudaFree(d_l); if(d_r)cudaFree(d_r); if(d_o)cudaFree(d_o);
    if(d_ls)cudaFree(d_ls); if(d_rs)cudaFree(d_rs); if(d_os)cudaFree(d_os);
    return rc;
}

__global__ void unary_kernel(const float* in, int n, int mode, float* out) {
    int i=blockIdx.x*blockDim.x+threadIdx.x; if(i>=n)return;
    float x=in[i];
    if(mode==0) out[i]=expf(x);
    else if(mode==1) out[i]=logf(x);
    else if(mode==2) out[i]=tanhf(x);
    else if(mode==3) out[i]=1.0f/(1.0f+expf(-x));
    else out[i]=x>0.0f?x:0.0f;
}

extern "C" int sireikon_cuda_unary(const float* in,int n,int mode,float* out){
    float *d_i=nullptr,*d_o=nullptr; int rc=0;
    if((rc=alloc_copy_in(&d_i,in,n,"unary input")))goto done;
    if((rc=alloc_out(&d_o,n,"unary output")))goto done;
    {int t=256,b=(n+t-1)/t; unary_kernel<<<b,t>>>(d_i,n,mode,d_o); if((rc=check_launch("unary kernel")))goto done;}
    rc=copy_out(out,d_o,n,"unary result");
done: if(d_i)cudaFree(d_i); if(d_o)cudaFree(d_o); return rc;
}

__global__ void power_kernel(const float* in,int n,float p,float* out){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)out[i]=powf(in[i],p);} 
extern "C" int sireikon_cuda_power(const float* in,int n,float p,float* out){
    float *di=nullptr,*doo=nullptr;int rc=0;if((rc=alloc_copy_in(&di,in,n,"power input")))goto done;if((rc=alloc_out(&doo,n,"power output")))goto done;
    {int t=256,b=(n+t-1)/t;power_kernel<<<b,t>>>(di,n,p,doo);if((rc=check_launch("power kernel")))goto done;}rc=copy_out(out,doo,n,"power result");
done:if(di)cudaFree(di);if(doo)cudaFree(doo);return rc;}

__global__ void sum_kernel(const float* in,int n,float* out,int squares){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n){float v=in[i];atomicAdd(out,squares?v*v:v);}}
static int do_sum(const float* in,int n,float* out,int squares){float *di=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&di,in,n,"sum input")))goto done;if((rc=alloc_out(&do_,1,"sum output")))goto done;cudaMemset(do_,0,sizeof(float));{int t=256,b=(n+t-1)/t;sum_kernel<<<b,t>>>(di,n,do_,squares);if((rc=check_launch("sum kernel")))goto done;}rc=copy_out(out,do_,1,"sum result");done:if(di)cudaFree(di);if(do_)cudaFree(do_);return rc;}
extern "C" int sireikon_cuda_sum(const float* in,int n,float* out){return do_sum(in,n,out,0);} 
extern "C" int sireikon_cuda_sum_squares(const float* in,int n,float* out){return do_sum(in,n,out,1);} 

__global__ void scale_kernel(const float* in,int n,float s,float* out){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i<n)out[i]=in[i]*s;}
extern "C" int sireikon_cuda_scale(const float* in,int n,float s,float* out){float *di=nullptr,*doo=nullptr;int rc=0;if((rc=alloc_copy_in(&di,in,n,"scale input")))goto done;if((rc=alloc_out(&doo,n,"scale output")))goto done;{int t=256,b=(n+t-1)/t;scale_kernel<<<b,t>>>(di,n,s,doo);if((rc=check_launch("scale kernel")))goto done;}rc=copy_out(out,doo,n,"scale result");done:if(di)cudaFree(di);if(doo)cudaFree(doo);return rc;}

__global__ void transpose_kernel(const float* in,int rows,int cols,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;int n=rows*cols;if(idx<n){int r=idx/cols,c=idx%cols;out[c*rows+r]=in[idx];}}
extern "C" int sireikon_cuda_transpose2d(const float* in,int rows,int cols,float* out){int n=rows*cols;float *di=nullptr,*doo=nullptr;int rc=0;if((rc=alloc_copy_in(&di,in,n,"transpose input")))goto done;if((rc=alloc_out(&doo,n,"transpose output")))goto done;{int t=256,b=(n+t-1)/t;transpose_kernel<<<b,t>>>(di,rows,cols,doo);if((rc=check_launch("transpose kernel")))goto done;}rc=copy_out(out,doo,n,"transpose result");done:if(di)cudaFree(di);if(doo)cudaFree(doo);return rc;}

__global__ void matmul_kernel(const float* a,const float* b,int m,int k,int n,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;int total=m*n;if(idx>=total)return;int r=idx/n,c=idx%n;float sum=0.0f;for(int x=0;x<k;++x)sum+=a[r*k+x]*b[x*n+c];out[idx]=sum;}
extern "C" int sireikon_cuda_matmul(const float* a,const float* b,int m,int k,int n,float* out){float *da=nullptr,*db=nullptr,*doo=nullptr;int rc=0;if((rc=alloc_copy_in(&da,a,m*k,"matmul A")))goto done;if((rc=alloc_copy_in(&db,b,k*n,"matmul B")))goto done;if((rc=alloc_out(&doo,m*n,"matmul output")))goto done;{int t=256,bl=(m*n+t-1)/t;matmul_kernel<<<bl,t>>>(da,db,m,k,n,doo);if((rc=check_launch("matmul kernel")))goto done;}rc=copy_out(out,doo,m*n,"matmul result");done:if(da)cudaFree(da);if(db)cudaFree(db);if(doo)cudaFree(doo);return rc;}

__global__ void attention_weights_kernel(const float* q,const float* k,int B,int Q,int K,int D,const int* mask,int mask_mode,float* weights){
    int row=blockIdx.x*blockDim.x+threadIdx.x; if(row>=B*Q)return; int b=row/Q,qi=row%Q; float scale=rsqrtf((float)D); float maxv=-INFINITY;
    for(int kj=0;kj<K;++kj){bool ok=true;if(mask_mode==1)ok=mask[qi*K+kj]!=0;else if(mask_mode==-1)ok=kj<=qi;if(!ok){weights[(b*Q+qi)*K+kj]=0.0f;continue;}float s=0.0f;for(int d=0;d<D;++d)s+=q[(b*Q+qi)*D+d]*k[(b*K+kj)*D+d];s*=scale;weights[(b*Q+qi)*K+kj]=s;if(s>maxv)maxv=s;}
    float denom=0.0f;for(int kj=0;kj<K;++kj){bool ok=true;if(mask_mode==1)ok=mask[qi*K+kj]!=0;else if(mask_mode==-1)ok=kj<=qi;if(ok){float e=expf(weights[(b*Q+qi)*K+kj]-maxv);weights[(b*Q+qi)*K+kj]=e;denom+=e;}}
    for(int kj=0;kj<K;++kj){bool ok=true;if(mask_mode==1)ok=mask[qi*K+kj]!=0;else if(mask_mode==-1)ok=kj<=qi;if(ok)weights[(b*Q+qi)*K+kj]/=denom;else weights[(b*Q+qi)*K+kj]=0.0f;}
}
__global__ void attention_output_kernel(const float* weights,const float* v,int B,int Q,int K,int D,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*Q*D)return;int d=idx%D;int row=idx/D;int b=row/Q,qi=row%Q;float sum=0.0f;for(int kj=0;kj<K;++kj)sum+=weights[(b*Q+qi)*K+kj]*v[(b*K+kj)*D+d];out[idx]=sum;}
extern "C" int sireikon_cuda_attention_forward(const float* q,const float* k,const float* v,int B,int Q,int K,int D,const int* mask,int mask_mode,float* out,float* weights){
    float *dq=nullptr,*dk=nullptr,*dv=nullptr,*do_=nullptr,*dw=nullptr;int *dm=nullptr;int rc=0;if((rc=alloc_copy_in(&dq,q,B*Q*D,"attention q")))goto done;if((rc=alloc_copy_in(&dk,k,B*K*D,"attention k")))goto done;if((rc=alloc_copy_in(&dv,v,B*K*D,"attention v")))goto done;if(mask_mode==1 && (rc=alloc_copy_in(&dm,mask,Q*K,"attention mask")))goto done;if((rc=alloc_out(&do_,B*Q*D,"attention out")))goto done;if((rc=alloc_out(&dw,B*Q*K,"attention weights")))goto done;
    {int t=128,b=(B*Q+t-1)/t;attention_weights_kernel<<<b,t>>>(dq,dk,B,Q,K,D,dm,mask_mode,dw);if((rc=check_launch("attention weights")))goto done;int total=B*Q*D;int b2=(total+t-1)/t;attention_output_kernel<<<b2,t>>>(dw,dv,B,Q,K,D,do_);if((rc=check_launch("attention output")))goto done;}
    if((rc=copy_out(out,do_,B*Q*D,"attention result")))goto done;rc=copy_out(weights,dw,B*Q*K,"attention weights result");
done:if(dq)cudaFree(dq);if(dk)cudaFree(dk);if(dv)cudaFree(dv);if(do_)cudaFree(do_);if(dw)cudaFree(dw);if(dm)cudaFree(dm);return rc;}

__global__ void attn_dv_kernel(const float* w,const float* up,int B,int Q,int K,int D,float* dv){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*K*D)return;int d=idx%D;int row=idx/D;int b=row/K,kj=row%K;float s=0.0f;for(int qi=0;qi<Q;++qi)s+=w[(b*Q+qi)*K+kj]*up[(b*Q+qi)*D+d];dv[idx]=s;}
__global__ void attn_dw_kernel(const float* v,const float* up,int B,int Q,int K,int D,float* dw){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*Q*K)return;int kj=idx%K;int row=idx/K;int b=row/Q,qi=row%Q;float s=0.0f;for(int d=0;d<D;++d)s+=up[(b*Q+qi)*D+d]*v[(b*K+kj)*D+d];dw[idx]=s;}
__global__ void attn_ds_kernel(const float* w,const float* dw,int B,int Q,int K,float* ds){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*Q*K)return;int kj=idx%K;int row=idx/K;float weighted=0.0f;for(int t=0;t<K;++t)weighted+=dw[row*K+t]*w[row*K+t];float ww=w[idx];ds[idx]=ww*(dw[idx]-weighted);}
__global__ void attn_dq_kernel(const float* k,const float* ds,int B,int Q,int K,int D,float* dq){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*Q*D)return;int d=idx%D;int row=idx/D;int b=row/Q,qi=row%Q;float scale=rsqrtf((float)D),s=0.0f;for(int kj=0;kj<K;++kj)s+=scale*ds[(b*Q+qi)*K+kj]*k[(b*K+kj)*D+d];dq[idx]=s;}
__global__ void attn_dk_kernel(const float* q,const float* ds,int B,int Q,int K,int D,float* dk){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=B*K*D)return;int d=idx%D;int row=idx/D;int b=row/K,kj=row%K;float scale=rsqrtf((float)D),s=0.0f;for(int qi=0;qi<Q;++qi)s+=scale*ds[(b*Q+qi)*K+kj]*q[(b*Q+qi)*D+d];dk[idx]=s;}
extern "C" int sireikon_cuda_attention_backward(const float* q,const float* k,const float* v,const float* w,const float* up,int B,int Q,int K,int D,float* dq,float* dk,float* dv){
    float *d_q=nullptr,*d_k=nullptr,*d_v=nullptr,*d_w=nullptr,*d_up=nullptr,*d_dq=nullptr,*d_dk=nullptr,*d_dv=nullptr,*d_dw=nullptr,*d_ds=nullptr;int rc=0;
    if((rc=alloc_copy_in(&d_q,q,B*Q*D,"attn backward q")))goto done;if((rc=alloc_copy_in(&d_k,k,B*K*D,"attn backward k")))goto done;if((rc=alloc_copy_in(&d_v,v,B*K*D,"attn backward v")))goto done;if((rc=alloc_copy_in(&d_w,w,B*Q*K,"attn backward w")))goto done;if((rc=alloc_copy_in(&d_up,up,B*Q*D,"attn backward up")))goto done;
    if((rc=alloc_out(&d_dq,B*Q*D,"attn dq")))goto done;if((rc=alloc_out(&d_dk,B*K*D,"attn dk")))goto done;if((rc=alloc_out(&d_dv,B*K*D,"attn dv")))goto done;if((rc=alloc_out(&d_dw,B*Q*K,"attn dw")))goto done;if((rc=alloc_out(&d_ds,B*Q*K,"attn ds")))goto done;
    {int t=128;int a=(B*K*D+t-1)/t;attn_dv_kernel<<<a,t>>>(d_w,d_up,B,Q,K,D,d_dv);if((rc=check_launch("attn dV")))goto done;int bw=(B*Q*K+t-1)/t;attn_dw_kernel<<<bw,t>>>(d_v,d_up,B,Q,K,D,d_dw);if((rc=check_launch("attn dW")))goto done;attn_ds_kernel<<<bw,t>>>(d_w,d_dw,B,Q,K,d_ds);if((rc=check_launch("attn dScore")))goto done;int bq=(B*Q*D+t-1)/t;attn_dq_kernel<<<bq,t>>>(d_k,d_ds,B,Q,K,D,d_dq);if((rc=check_launch("attn dQ")))goto done;attn_dk_kernel<<<a,t>>>(d_q,d_ds,B,Q,K,D,d_dk);if((rc=check_launch("attn dK")))goto done;}
    if((rc=copy_out(dq,d_dq,B*Q*D,"attn dq result")))goto done;if((rc=copy_out(dk,d_dk,B*K*D,"attn dk result")))goto done;rc=copy_out(dv,d_dv,B*K*D,"attn dv result");
done:if(d_q)cudaFree(d_q);if(d_k)cudaFree(d_k);if(d_v)cudaFree(d_v);if(d_w)cudaFree(d_w);if(d_up)cudaFree(d_up);if(d_dq)cudaFree(d_dq);if(d_dk)cudaFree(d_dk);if(d_dv)cudaFree(d_dv);if(d_dw)cudaFree(d_dw);if(d_ds)cudaFree(d_ds);return rc;}

__global__ void layernorm_forward_kernel(const float* x,const float* gamma,const float* beta,int rows,int width,float eps,int affine,float* out,float* norm,float* inv){int row=blockIdx.x*blockDim.x+threadIdx.x;if(row>=rows)return;int start=row*width;float mean=0.0f;for(int j=0;j<width;++j)mean+=x[start+j];mean/=width;float var=0.0f;for(int j=0;j<width;++j){float d=x[start+j]-mean;var+=d*d;}var/=width;float is=rsqrtf(var+eps);inv[row]=is;for(int j=0;j<width;++j){float h=(x[start+j]-mean)*is;norm[start+j]=h;out[start+j]=affine?(h*gamma[j]+beta[j]):h;}}
extern "C" int sireikon_cuda_layernorm_forward(const float* x,const float* gamma,const float* beta,int rows,int width,float eps,int affine,float* out,float* norm,float* inv){float *dx=nullptr,*dg=nullptr,*db=nullptr,*doo=nullptr,*dn=nullptr,*di=nullptr;int rc=0;if((rc=alloc_copy_in(&dx,x,rows*width,"ln x")))goto done;if(affine){if((rc=alloc_copy_in(&dg,gamma,width,"ln gamma")))goto done;if((rc=alloc_copy_in(&db,beta,width,"ln beta")))goto done;}if((rc=alloc_out(&doo,rows*width,"ln out")))goto done;if((rc=alloc_out(&dn,rows*width,"ln norm")))goto done;if((rc=alloc_out(&di,rows,"ln inv")))goto done;{int t=128,b=(rows+t-1)/t;layernorm_forward_kernel<<<b,t>>>(dx,dg,db,rows,width,eps,affine,doo,dn,di);if((rc=check_launch("layernorm forward")))goto done;}if((rc=copy_out(out,doo,rows*width,"ln out result")))goto done;if((rc=copy_out(norm,dn,rows*width,"ln norm result")))goto done;rc=copy_out(inv,di,rows,"ln inv result");done:if(dx)cudaFree(dx);if(dg)cudaFree(dg);if(db)cudaFree(db);if(doo)cudaFree(doo);if(dn)cudaFree(dn);if(di)cudaFree(di);return rc;}

__global__ void layernorm_dx_kernel(const float* up,const float* norm,const float* inv,const float* gamma,int rows,int width,int affine,float* dx){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=rows*width)return;int row=idx/width,j=idx%width,start=row*width;float sumdy=0.0f,sumdyx=0.0f;for(int t=0;t<width;++t){float dy=up[start+t]*(affine?gamma[t]:1.0f);sumdy+=dy;sumdyx+=dy*norm[start+t];}float dy=up[idx]*(affine?gamma[j]:1.0f);dx[idx]=inv[row]/width*(width*dy-sumdy-norm[idx]*sumdyx);}
__global__ void layernorm_param_kernel(const float* up,const float* norm,int rows,int width,float* dg,float* db){int j=blockIdx.x*blockDim.x+threadIdx.x;if(j>=width)return;float g=0.0f,b=0.0f;for(int r=0;r<rows;++r){int idx=r*width+j;g+=up[idx]*norm[idx];b+=up[idx];}dg[j]=g;db[j]=b;}
extern "C" int sireikon_cuda_layernorm_backward(const float* up,const float* norm,const float* inv,const float* gamma,const float* unused,int rows,int width,int affine,float* dx,float* dg,float* db){(void)unused;float *du=nullptr,*dn=nullptr,*di=nullptr,*dga=nullptr,*ddx=nullptr,*ddg=nullptr,*ddb=nullptr;int rc=0;if((rc=alloc_copy_in(&du,up,rows*width,"ln back up")))goto done;if((rc=alloc_copy_in(&dn,norm,rows*width,"ln back norm")))goto done;if((rc=alloc_copy_in(&di,inv,rows,"ln back inv")))goto done;if(affine && (rc=alloc_copy_in(&dga,gamma,width,"ln back gamma")))goto done;if((rc=alloc_out(&ddx,rows*width,"ln back dx")))goto done;if((rc=alloc_out(&ddg,width,"ln back dg")))goto done;if((rc=alloc_out(&ddb,width,"ln back db")))goto done;cudaMemset(ddg,0,width*sizeof(float));cudaMemset(ddb,0,width*sizeof(float));{int t=128,b=(rows*width+t-1)/t;layernorm_dx_kernel<<<b,t>>>(du,dn,di,dga,rows,width,affine,ddx);if((rc=check_launch("layernorm dx")))goto done;if(affine){int bp=(width+t-1)/t;layernorm_param_kernel<<<bp,t>>>(du,dn,rows,width,ddg,ddb);if((rc=check_launch("layernorm params")))goto done;}}if((rc=copy_out(dx,ddx,rows*width,"ln dx result")))goto done;if((rc=copy_out(dg,ddg,width,"ln dg result")))goto done;rc=copy_out(db,ddb,width,"ln db result");done:if(du)cudaFree(du);if(dn)cudaFree(dn);if(di)cudaFree(di);if(dga)cudaFree(dga);if(ddx)cudaFree(ddx);if(ddg)cudaFree(ddg);if(ddb)cudaFree(ddb);return rc;}

__global__ void embedding_forward_kernel(const float* w,const int* ids,int count,int vocab,int dim,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=count*dim)return;int row=idx/dim,j=idx%dim;int token=ids[row];out[idx]=(token>=0&&token<vocab)?w[token*dim+j]:0.0f;}
extern "C" int sireikon_cuda_embedding_forward(const float* w,const int* ids,int count,int vocab,int dim,float* out){float *dw=nullptr,*doo=nullptr;int *di=nullptr;int rc=0;if((rc=alloc_copy_in(&dw,w,vocab*dim,"emb w")))goto done;if((rc=alloc_copy_in(&di,ids,count,"emb ids")))goto done;if((rc=alloc_out(&doo,count*dim,"emb out")))goto done;{int t=256,b=(count*dim+t-1)/t;embedding_forward_kernel<<<b,t>>>(dw,di,count,vocab,dim,doo);if((rc=check_launch("embedding forward")))goto done;}rc=copy_out(out,doo,count*dim,"emb result");done:if(dw)cudaFree(dw);if(di)cudaFree(di);if(doo)cudaFree(doo);return rc;}
__global__ void embedding_backward_kernel(const float* up,const int* ids,int count,int vocab,int dim,int padding,float* grad){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=count*dim)return;int row=idx/dim,j=idx%dim;int token=ids[row];if(token>=0&&token<vocab&&token!=padding)atomicAdd(&grad[token*dim+j],up[idx]);}
extern "C" int sireikon_cuda_embedding_backward(const float* up,const int* ids,int count,int vocab,int dim,int padding,float* grad){float *du=nullptr,*dg=nullptr;int *di=nullptr;int rc=0;if((rc=alloc_copy_in(&du,up,count*dim,"emb back up")))goto done;if((rc=alloc_copy_in(&di,ids,count,"emb back ids")))goto done;if((rc=alloc_out(&dg,vocab*dim,"emb grad")))goto done;cudaMemset(dg,0,vocab*dim*sizeof(float));{int t=256,b=(count*dim+t-1)/t;embedding_backward_kernel<<<b,t>>>(du,di,count,vocab,dim,padding,dg);if((rc=check_launch("embedding backward")))goto done;}rc=copy_out(grad,dg,vocab*dim,"emb grad result");done:if(du)cudaFree(du);if(di)cudaFree(di);if(dg)cudaFree(dg);return rc;}

__global__ void cross_entropy_forward_kernel(const float* x,const int* targets,int rows,int classes,int ignore,float smoothing,float* probs,float* losses,int* active){int row=blockIdx.x*blockDim.x+threadIdx.x;if(row>=rows)return;int target=targets[row],start=row*classes;if(target==ignore){active[row]=0;losses[row]=0.0f;for(int j=0;j<classes;++j)probs[start+j]=0.0f;return;}active[row]=1;float maxv=x[start];for(int j=1;j<classes;++j)if(x[start+j]>maxv)maxv=x[start+j];float denom=0.0f;for(int j=0;j<classes;++j){float e=expf(x[start+j]-maxv);probs[start+j]=e;denom+=e;}float logsum=maxv+logf(denom),avg=0.0f;for(int j=0;j<classes;++j){probs[start+j]/=denom;avg+=-(x[start+j]-logsum);}avg/=classes;float targetloss=-(x[start+target]-logsum);losses[row]=(1.0f-smoothing)*targetloss+smoothing*avg;}
extern "C" int sireikon_cuda_cross_entropy_forward(const float* x,const int* targets,int rows,int classes,int ignore,float smoothing,float* probs,float* losses,int* active){float *dx=nullptr,*dp=nullptr,*dl=nullptr;int *dt=nullptr,*da=nullptr;int rc=0;if((rc=alloc_copy_in(&dx,x,rows*classes,"ce x")))goto done;if((rc=alloc_copy_in(&dt,targets,rows,"ce targets")))goto done;if((rc=alloc_out(&dp,rows*classes,"ce probs")))goto done;if((rc=alloc_out(&dl,rows,"ce losses")))goto done;if((rc=alloc_out(&da,rows,"ce active")))goto done;{int t=128,b=(rows+t-1)/t;cross_entropy_forward_kernel<<<b,t>>>(dx,dt,rows,classes,ignore,smoothing,dp,dl,da);if((rc=check_launch("cross entropy forward")))goto done;}if((rc=copy_out(probs,dp,rows*classes,"ce probs result")))goto done;if((rc=copy_out(losses,dl,rows,"ce losses result")))goto done;rc=copy_out(active,da,rows,"ce active result");done:if(dx)cudaFree(dx);if(dt)cudaFree(dt);if(dp)cudaFree(dp);if(dl)cudaFree(dl);if(da)cudaFree(da);return rc;}
__global__ void cross_entropy_backward_kernel(const float* probs,const int* targets,const int* active,const float* upstream,int rows,int classes,float smoothing,float active_count,int reduction,float* grad){int idx=blockIdx.x*blockDim.x+threadIdx.x;if(idx>=rows*classes)return;int row=idx/classes,j=idx%classes;if(!active[row]){grad[idx]=0.0f;return;}float up=(reduction==0)?upstream[row]:upstream[0];if(reduction==2)up/=active_count;float tp=smoothing/classes;if(j==targets[row])tp+=1.0f-smoothing;grad[idx]=(probs[idx]-tp)*up;}
extern "C" int sireikon_cuda_cross_entropy_backward(const float* probs,const int* targets,const int* active,const float* upstream,int rows,int classes,float smoothing,float active_count,int reduction,int unused,float* grad){(void)unused;float *dp=nullptr,*du=nullptr,*dg=nullptr;int *dt=nullptr,*da=nullptr;int rc=0;int upn=(reduction==0)?rows:1;if((rc=alloc_copy_in(&dp,probs,rows*classes,"ce back probs")))goto done;if((rc=alloc_copy_in(&dt,targets,rows,"ce back targets")))goto done;if((rc=alloc_copy_in(&da,active,rows,"ce back active")))goto done;if((rc=alloc_copy_in(&du,upstream,upn,"ce back upstream")))goto done;if((rc=alloc_out(&dg,rows*classes,"ce back grad")))goto done;{int t=256,b=(rows*classes+t-1)/t;cross_entropy_backward_kernel<<<b,t>>>(dp,dt,da,du,rows,classes,smoothing,active_count,reduction,dg);if((rc=check_launch("cross entropy backward")))goto done;}rc=copy_out(grad,dg,rows*classes,"ce grad result");done:if(dp)cudaFree(dp);if(dt)cudaFree(dt);if(da)cudaFree(da);if(du)cudaFree(du);if(dg)cudaFree(dg);return rc;}

__global__ void adamw_kernel(const float* values,const float* grads,const float* first,const float* second,int n,float lr,float b1,float b2,float eps,float decay,float scale,float bc1,float bc2,float* outv,float* outm,float* outs){int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;float g=grads[i]*scale;float m=b1*first[i]+(1.0f-b1)*g;float s=b2*second[i]+(1.0f-b2)*g*g;float mh=m/bc1,sh=s/bc2;float p=values[i];if(decay!=0.0f)p*=1.0f-lr*decay;p-=lr*(mh/(sqrtf(sh)+eps));outv[i]=p;outm[i]=m;outs[i]=s;}
extern "C" int sireikon_cuda_adamw(const float* values,const float* grads,const float* first,const float* second,int n,float lr,float b1,float b2,float eps,float decay,float scale,float bc1,float bc2,float* outv,float* outm,float* outs){float *dv=nullptr,*dg=nullptr,*dm=nullptr,*ds=nullptr,*dov=nullptr,*dom=nullptr,*dos=nullptr;int rc=0;if((rc=alloc_copy_in(&dv,values,n,"adam values")))goto done;if((rc=alloc_copy_in(&dg,grads,n,"adam grads")))goto done;if((rc=alloc_copy_in(&dm,first,n,"adam first")))goto done;if((rc=alloc_copy_in(&ds,second,n,"adam second")))goto done;if((rc=alloc_out(&dov,n,"adam out values")))goto done;if((rc=alloc_out(&dom,n,"adam out first")))goto done;if((rc=alloc_out(&dos,n,"adam out second")))goto done;{int t=256,b=(n+t-1)/t;adamw_kernel<<<b,t>>>(dv,dg,dm,ds,n,lr,b1,b2,eps,decay,scale,bc1,bc2,dov,dom,dos);if((rc=check_launch("adamw kernel")))goto done;}if((rc=copy_out(outv,dov,n,"adam values result")))goto done;if((rc=copy_out(outm,dom,n,"adam first result")))goto done;rc=copy_out(outs,dos,n,"adam second result");done:if(dv)cudaFree(dv);if(dg)cudaFree(dg);if(dm)cudaFree(dm);if(ds)cudaFree(ds);if(dov)cudaFree(dov);if(dom)cudaFree(dom);if(dos)cudaFree(dos);return rc;}

__global__ void activation_backward_kernel(const float* source,const float* output,const float* upstream,int n,int mode,float parameter,float* grad){
    int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;float d=0.0f;
    if(mode==0)d=output[i];
    else if(mode==1)d=1.0f/source[i];
    else if(mode==2)d=1.0f-output[i]*output[i];
    else if(mode==3)d=output[i]*(1.0f-output[i]);
    else if(mode==4)d=source[i]>0.0f?1.0f:0.0f;
    else {d=(parameter==0.0f)?0.0f:parameter*powf(source[i],parameter-1.0f);} 
    grad[i]=upstream[i]*d;
}
extern "C" int sireikon_cuda_activation_backward(const float* source,const float* output,const float* upstream,int n,int mode,float parameter,float* grad){
    float *ds=nullptr,*do_=nullptr,*du=nullptr,*dg=nullptr;int rc=0;
    if((rc=alloc_copy_in(&ds,source,n,"activation back source")))goto done;
    if((rc=alloc_copy_in(&do_,output,n,"activation back output")))goto done;
    if((rc=alloc_copy_in(&du,upstream,n,"activation back upstream")))goto done;
    if((rc=alloc_out(&dg,n,"activation back grad")))goto done;
    {int t=256,b=(n+t-1)/t;activation_backward_kernel<<<b,t>>>(ds,do_,du,n,mode,parameter,dg);if((rc=check_launch("activation backward")))goto done;}
    rc=copy_out(grad,dg,n,"activation back result");
done:if(ds)cudaFree(ds);if(do_)cudaFree(do_);if(du)cudaFree(du);if(dg)cudaFree(dg);return rc;
}

__global__ void extract_head_kernel(const float* source,int batch,int sequence,int d_model,int head_start,int head_dim,float* out){
    int idx=blockIdx.x*blockDim.x+threadIdx.x;int n=batch*sequence*head_dim;if(idx>=n)return;int d=idx%head_dim;int row=idx/head_dim;out[idx]=source[row*d_model+head_start+d];
}
extern "C" int sireikon_cuda_extract_head(const float* source,int batch,int sequence,int d_model,int head_start,int head_dim,float* out){int n=batch*sequence*head_dim,total=batch*sequence*d_model;float *ds=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&ds,source,total,"extract head source")))goto done;if((rc=alloc_out(&do_,n,"extract head output")))goto done;{int t=256,b=(n+t-1)/t;extract_head_kernel<<<b,t>>>(ds,batch,sequence,d_model,head_start,head_dim,do_);if((rc=check_launch("extract head")))goto done;}rc=copy_out(out,do_,n,"extract head result");done:if(ds)cudaFree(ds);if(do_)cudaFree(do_);return rc;}

__global__ void scatter_head_kernel(const float* upstream,int batch,int sequence,int d_model,int head_start,int head_dim,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;int n=batch*sequence*head_dim;if(idx>=n)return;int d=idx%head_dim;int row=idx/head_dim;out[row*d_model+head_start+d]=upstream[idx];}
extern "C" int sireikon_cuda_scatter_head(const float* upstream,int batch,int sequence,int d_model,int head_start,int head_dim,float* out){int n=batch*sequence*head_dim,total=batch*sequence*d_model;float *du=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&du,upstream,n,"scatter head upstream")))goto done;if((rc=alloc_out(&do_,total,"scatter head output")))goto done;cudaMemset(do_,0,total*sizeof(float));{int t=256,b=(n+t-1)/t;scatter_head_kernel<<<b,t>>>(du,batch,sequence,d_model,head_start,head_dim,do_);if((rc=check_launch("scatter head")))goto done;}rc=copy_out(out,do_,total,"scatter head result");done:if(du)cudaFree(du);if(do_)cudaFree(do_);return rc;}

__global__ void concat_heads_kernel(const float* heads,int batch,int sequence,int num_heads,int head_dim,float* out){int d_model=num_heads*head_dim;int idx=blockIdx.x*blockDim.x+threadIdx.x;int n=batch*sequence*d_model;if(idx>=n)return;int d=idx%d_model;int row=idx/d_model;int h=d/head_dim;int hd=d%head_dim;int head_size=batch*sequence*head_dim;out[idx]=heads[h*head_size+row*head_dim+hd];}
extern "C" int sireikon_cuda_concat_heads(const float* heads,int batch,int sequence,int num_heads,int head_dim,float* out){int d_model=num_heads*head_dim,total=batch*sequence*d_model;float *dh=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&dh,heads,total,"concat heads input")))goto done;if((rc=alloc_out(&do_,total,"concat heads output")))goto done;{int t=256,b=(total+t-1)/t;concat_heads_kernel<<<b,t>>>(dh,batch,sequence,num_heads,head_dim,do_);if((rc=check_launch("concat heads")))goto done;}rc=copy_out(out,do_,total,"concat heads result");done:if(dh)cudaFree(dh);if(do_)cudaFree(do_);return rc;}

__global__ void split_head_grad_kernel(const float* upstream,int batch,int sequence,int num_heads,int head_dim,int head_index,float* out){int d_model=num_heads*head_dim;int idx=blockIdx.x*blockDim.x+threadIdx.x;int n=batch*sequence*head_dim;if(idx>=n)return;int d=idx%head_dim;int row=idx/head_dim;out[idx]=upstream[row*d_model+head_index*head_dim+d];}
extern "C" int sireikon_cuda_split_head_grad(const float* upstream,int batch,int sequence,int num_heads,int head_dim,int head_index,float* out){int d_model=num_heads*head_dim,total=batch*sequence*d_model,n=batch*sequence*head_dim;float *du=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&du,upstream,total,"split head upstream")))goto done;if((rc=alloc_out(&do_,n,"split head output")))goto done;{int t=256,b=(n+t-1)/t;split_head_grad_kernel<<<b,t>>>(du,batch,sequence,num_heads,head_dim,head_index,do_);if((rc=check_launch("split head grad")))goto done;}rc=copy_out(out,do_,n,"split head result");done:if(du)cudaFree(du);if(do_)cudaFree(do_);return rc;}

__global__ void rope_forward_kernel(const float* source,int batch,int sequence,int head_dim,int position_offset,float base,float* out){int idx=blockIdx.x*blockDim.x+threadIdx.x;int pairs=batch*sequence*(head_dim/2);if(idx>=pairs)return;int pair=idx%(head_dim/2);int row=idx/(head_dim/2);int pos=row%sequence;int even=2*pair,odd=even+1;float exponent=(2.0f*pair)/head_dim;float angle=(pos+position_offset)/powf(base,exponent);float c=cosf(angle),s=sinf(angle);int eidx=row*head_dim+even,oidx=eidx+1;float ev=source[eidx],ov=source[oidx];out[eidx]=ev*c-ov*s;out[oidx]=ev*s+ov*c;}
extern "C" int sireikon_cuda_rope_forward(const float* source,int batch,int sequence,int head_dim,int position_offset,float base,float* out){int total=batch*sequence*head_dim,pairs=batch*sequence*(head_dim/2);float *ds=nullptr,*do_=nullptr;int rc=0;if((rc=alloc_copy_in(&ds,source,total,"rope source")))goto done;if((rc=alloc_out(&do_,total,"rope output")))goto done;{int t=256,b=(pairs+t-1)/t;rope_forward_kernel<<<b,t>>>(ds,batch,sequence,head_dim,position_offset,base,do_);if((rc=check_launch("rope forward")))goto done;}rc=copy_out(out,do_,total,"rope result");done:if(ds)cudaFree(ds);if(do_)cudaFree(do_);return rc;}

__global__ void rope_backward_kernel(const float* upstream,int batch,int sequence,int head_dim,int position_offset,float base,float* grad){int idx=blockIdx.x*blockDim.x+threadIdx.x;int pairs=batch*sequence*(head_dim/2);if(idx>=pairs)return;int pair=idx%(head_dim/2);int row=idx/(head_dim/2);int pos=row%sequence;int even=2*pair;float exponent=(2.0f*pair)/head_dim;float angle=(pos+position_offset)/powf(base,exponent);float c=cosf(angle),s=sinf(angle);int eidx=row*head_dim+even,oidx=eidx+1;float de=upstream[eidx],doo=upstream[oidx];grad[eidx]=de*c+doo*s;grad[oidx]=-de*s+doo*c;}
extern "C" int sireikon_cuda_rope_backward(const float* upstream,int batch,int sequence,int head_dim,int position_offset,float base,float* grad){int total=batch*sequence*head_dim,pairs=batch*sequence*(head_dim/2);float *du=nullptr,*dg=nullptr;int rc=0;if((rc=alloc_copy_in(&du,upstream,total,"rope back upstream")))goto done;if((rc=alloc_out(&dg,total,"rope back grad")))goto done;{int t=256,b=(pairs+t-1)/t;rope_backward_kernel<<<b,t>>>(du,batch,sequence,head_dim,position_offset,base,dg);if((rc=check_launch("rope backward")))goto done;}rc=copy_out(grad,dg,total,"rope back result");done:if(du)cudaFree(du);if(dg)cudaFree(dg);return rc;}
